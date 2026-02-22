# pylint: disable=duplicate-code
import gc
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from PIL import Image
import torch
from transformers import (
    AutoImageProcessor,
    DFineForObjectDetection,
)

from preprocessor.config.step_configs import ObjectDetectionConfig
from preprocessor.core.artifacts import (
    FrameCollection,
    ObjectDetectionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import (
    JsonFileOutput,
    OutputDescriptor,
)
from preprocessor.services.io.files import FileOperations


class ObjectDetectionStep(
    PipelineStep[FrameCollection, ObjectDetectionData, ObjectDetectionConfig],
):
    def __init__(self, config: ObjectDetectionConfig) -> None:
        super().__init__(config)
        self.__model: Optional[DFineForObjectDetection] = None
        self.__image_processor: Optional[AutoImageProcessor] = None

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__model is None:
            self.__load_model(context)

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__model:
            self.__unload_model(context)

    def cleanup(self) -> None:
        self.__model = None
        self.__image_processor = None

    def execute_batch(
        self, input_data: List[FrameCollection], context: ExecutionContext,
    ) -> List[ObjectDetectionData]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> ObjectDetectionData:
        output_path = self._get_cache_path(input_data, context)
        self.__ensure_model_loaded(context)

        frame_files = self.__extract_frame_files(input_data)
        if not frame_files:
            context.logger.warning(f'No frame files found in {input_data.directory}')
            return ObjectDetectionData(
                episode_id=input_data.episode_id,
                episode_info=input_data.episode_info,
                path=output_path,
            )

        detections = self.__process_batches(frame_files)
        self.__save_results(detections, output_path, input_data, context, frame_files)

        return ObjectDetectionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
        )

    def get_output_descriptors(self) -> List[OutputDescriptor]:
        return [
            JsonFileOutput(
                subdir="detections/objects",
                pattern="{season}/{episode}.json",
                min_size_bytes=10,
            ),
        ]

    def _get_cache_path(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0,
            context,
            self.__create_path_variables(input_data),
        )

    def _load_from_cache(
        self, cache_path: Path, input_data: FrameCollection, context: ExecutionContext,
    ) -> ObjectDetectionData:
        return ObjectDetectionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=cache_path,
        )

    def __ensure_model_loaded(self, context: ExecutionContext) -> None:
        if self.__model is None:
            self.__load_model(context)

    def __load_model(self, context: ExecutionContext) -> None:
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA is not available. Object detection requires GPU.')

        context.logger.info(f'Loading D-FINE model: {self.config.model_name}')
        self.__image_processor = AutoImageProcessor.from_pretrained(self.config.model_name)
        self.__model = DFineForObjectDetection.from_pretrained(self.config.model_name)
        self.__model.to('cuda')
        context.logger.info('D-FINE model loaded on GPU')

    def __unload_model(self, context: ExecutionContext) -> None:
        context.logger.info('Object Detection model unloaded')
        self.__model = None
        self.__image_processor = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def __process_batches(self, frame_files: List[Path]) -> List[Dict[str, Any]]:
        detections: List[Dict[str, Any]] = []

        for batch_start in range(0, len(frame_files), self.config.batch_size):
            batch_paths = frame_files[batch_start:batch_start + self.config.batch_size]
            batch_detections = self.__process_single_batch(batch_paths)
            detections.extend(batch_detections)

        return detections

    def __process_single_batch(self, batch_paths: List[Path]) -> List[Dict[str, Any]]:
        batch_images = [Image.open(fp) for fp in batch_paths]
        target_sizes = [(img.height, img.width) for img in batch_images]

        inputs = self.__image_processor(images=batch_images, return_tensors='pt')
        inputs = {k: v.to('cuda') for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.__model(**inputs)

        results = self.__image_processor.post_process_object_detection(
            outputs,
            target_sizes=target_sizes,
            threshold=self.config.conf_threshold,
        )

        batch_detections = []
        for frame_path, result in zip(batch_paths, results):
            frame_entry = self.__build_frame_entry(frame_path, result)
            if frame_entry['objects']:
                batch_detections.append(frame_entry)

        for img in batch_images:
            img.close()

        return batch_detections

    def __build_frame_entry(
        self, frame_path: Path, result: Dict[str, Any],
    ) -> Dict[str, Any]:
        objects: List[Dict[str, Any]] = []
        for score, label_id, box in zip(result['scores'], result['labels'], result['boxes']):
            box_coords = [float(v) for v in box.tolist()]
            objects.append({
                'class_id': label_id.item(),
                'class_name': self.__model.config.id2label[label_id.item()],
                'confidence': score.item(),
                'bbox': {
                    'x1': box_coords[0],
                    'y1': box_coords[1],
                    'x2': box_coords[2],
                    'y2': box_coords[3],
                },
            })
        return {'frame': frame_path.name, 'objects': objects}

    def __save_results(
        self,
        detections: List[Dict[str, Any]],
        output_path: Path,
        input_data: FrameCollection,
        context: ExecutionContext,
        frame_files: List[Path],
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_data: Dict[str, Any] = {
            'episode_id': input_data.episode_id,
            'series_name': context.series_name,
            'detection_settings': self.config.model_dump(),
            'statistics': {
                'total_frames_processed': len(frame_files),
                'frames_with_detections': len(detections),
                'object_counts': self.__count_objects(detections),
            },
            'detections': detections,
        }
        FileOperations.atomic_write_json(output_path, output_data)

    @staticmethod
    def __create_path_variables(input_data: FrameCollection) -> Dict[str, str]:
        return {
            'season': f'S{input_data.episode_info.season:02d}',
            'episode': input_data.episode_info.episode_code(),
        }

    @staticmethod
    def __extract_frame_files(input_data: FrameCollection) -> List[Path]:
        return sorted([
            f for f in input_data.directory.glob('*.jpg')
            if f.is_file() and 'frame_' in f.name
        ])

    @staticmethod
    def __count_objects(detections: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for frame in detections:
            for obj in frame.get('objects', []):
                name: str = obj.get('class_name', 'unknown')
                counts[name] = counts.get(name, 0) + 1
        return counts
