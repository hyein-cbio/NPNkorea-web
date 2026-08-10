"""Static lookup data for Korea's National Point Number bands."""

DIGIT_ROWS = (
    (1, "Ga", "가"),
    (2, "Na", "나"),
    (3, "Da", "다"),
    (4, "Ra", "라"),
    (5, "Ma", "마"),
    (6, "Ba", "바"),
    (7, "Sa", "사"),
    (8, "A", "아"),
    (9, "Ja", "자"),
    (10, "Cha", "차"),
    (11, "Ka", "카"),
    (12, "Ta", "타"),
    (13, "Pa", "파"),
    (14, "Ha", "하"),
)

DIGIT_TO_ABC = {digit: abc for digit, abc, _ in DIGIT_ROWS}
DIGIT_TO_HAN = {digit: han for digit, _, han in DIGIT_ROWS}
ABC_TO_DIGIT = {abc.upper(): digit for digit, abc, _ in DIGIT_ROWS}
HAN_TO_DIGIT = {han: digit for digit, _, han in DIGIT_ROWS}
VALID_DIGITS = frozenset(DIGIT_TO_HAN)
MAX_BATCH_SIZE = 1_000
ABC_CODES_SORTED = tuple(sorted(ABC_TO_DIGIT, key=len, reverse=True))
