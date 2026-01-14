import click

from preprocessor.cli.commands import (
    analyze_text,
    detect_scenes,
    export_frames,
    generate_elastic_documents,
    generate_embeddings,
    image_hashing,
    import_transcriptions,
    index,
    run_all,
    scrape_episodes,
    search,
    transcode,
    transcribe,
    transcribe_elevenlabs,
    validate,
)


@click.group()
@click.help_option("-h", "--help")
def cli():
    """Preprocessor CLI for video processing pipeline."""


# noinspection PyTypeChecker
cli.add_command(transcode)
# noinspection PyTypeChecker
cli.add_command(transcribe)
# noinspection PyTypeChecker
cli.add_command(index)
# noinspection PyTypeChecker
cli.add_command(import_transcriptions)
# noinspection PyTypeChecker
cli.add_command(transcribe_elevenlabs)
# noinspection PyTypeChecker
cli.add_command(scrape_episodes)
# noinspection PyTypeChecker
cli.add_command(detect_scenes)
# noinspection PyTypeChecker
cli.add_command(export_frames)
# noinspection PyTypeChecker
cli.add_command(image_hashing)
# noinspection PyTypeChecker
cli.add_command(generate_embeddings)
# noinspection PyTypeChecker
cli.add_command(generate_elastic_documents)
# noinspection PyTypeChecker
cli.add_command(search)
# noinspection PyTypeChecker
cli.add_command(run_all)
# noinspection PyTypeChecker
cli.add_command(validate)
# noinspection PyTypeChecker
cli.add_command(analyze_text)


__all__ = ["cli"]
