from dataclasses import (
    asdict,
    dataclass,
)
from typing import (
    Any,
    Dict,
    Optional,
    Tuple,
)


@dataclass(frozen=True)
class FilterKeySpec:
    canonical: str
    aliases: Tuple[str, ...]
    value_format: str
    description_pl: str
    examples: Tuple[str, ...]
    list_command: Optional[str] = None

    @property
    def all_keys(self) -> Tuple[str, ...]:
        return (self.canonical, *self.aliases)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


FILTER_SCHEMA: Tuple[FilterKeySpec, ...] = (
    FilterKeySpec(
        canonical="sezon",
        aliases=("season", "s"),
        value_format="N | N,N | N-M",
        description_pl="Ogranicza wyniki do wybranych sezonów (lista lub zakres).",
        examples=("sezon:2", "sezon:1,3,5", "sezon:1-3"),
    ),
    FilterKeySpec(
        canonical="odcinek",
        aliases=("episode", "ep"),
        value_format="SxxExx | N | S01E03-S01E07 | SxxExx,SyyEzz",
        description_pl="Ogranicza do konkretnych odcinków.",
        examples=("odcinek:S01E05", "odcinek:5", "odcinek:S01E03-S01E07"),
    ),
    FilterKeySpec(
        canonical="tytul",
        aliases=("title", "t"),
        value_format="tekst (fuzzy match po tytule odcinka)",
        description_pl="Dopasowanie rozmyte do tytułu odcinka.",
        examples=("tytul:ranczo", "tytul:\"wielki mecz\""),
    ),
    FilterKeySpec(
        canonical="postac",
        aliases=("character", "p"),
        value_format="nazwa | nazwa,nazwa (grupa OR; kilka postac: AND)",
        description_pl="Postać widoczna w kadrze. Wartości w jednej grupie to OR, kolejne postac:... to AND.",
        examples=(
            "postac:Lucy",
            "postac:Lucy,Kusy",
            "postac:Lucy postac:Kusy",
        ),
        list_command="/postacie",
    ),
    FilterKeySpec(
        canonical="emocja",
        aliases=("emotion", "e"),
        value_format="nazwa | nazwa,nazwa (OR; akceptuje PL i EN oraz aliasy)",
        description_pl="Emocja postaci w kadrze. Akceptowane są polskie i angielskie nazwy plus aliasy (np. happy→happiness, radosny→happiness).",
        examples=(
            "emocja:radosny",
            "emocja:happy",
            "emocja:smutny,neutralny",
        ),
        list_command="/emocje",
    ),
    FilterKeySpec(
        canonical="obiekt",
        aliases=("object", "obj", "o"),
        value_format="nazwa[OPN] | nazwa,nazwa (OR; kilka obiekt: AND). OP: = > >= < <=",
        description_pl="Obiekt wykryty w kadrze (opcjonalnie z warunkiem ilości).",
        examples=(
            "obiekt:krzeslo",
            "obiekt:krzeslo>3",
            "obiekt:pies,kot",
            "obiekt:pies obiekt:smycz",
        ),
        list_command="/objl",
    ),
)


_ALIAS_INDEX: Dict[str, str] = {
    alias: spec.canonical
    for spec in FILTER_SCHEMA
    for alias in spec.all_keys
}


def alias_to_canonical(key: str) -> Optional[str]:
    return _ALIAS_INDEX.get(key.lower().strip())


def schema_as_dicts() -> Tuple[Dict[str, Any], ...]:
    return tuple(spec.to_dict() for spec in FILTER_SCHEMA)
