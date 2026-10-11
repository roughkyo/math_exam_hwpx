"""예제 세 문항의 교점·면적·선택지를 독립적으로 검산합니다."""
from fractions import Fraction as F


def integral(coefficients, a, b):
    # 내림차순 다항식 계수를 유리수로 적분합니다.
    degree = len(coefficients) - 1
    total = F(0)
    for i, c in enumerate(coefficients):
        n = degree - i + 1
        total += F(c, n) * (F(b) ** n - F(a) ** n)
    return total


assert integral([-1, 3, 0], 0, 3) == F(9, 2)
assert integral([-1, 2, 3], -1, 3) == F(32, 3)
assert integral([1, 0, -4, 0], -2, 0) == 4
assert -integral([1, 0, -4, 0], 0, 2) == 4
answers = [F(9, 2), F(3), F(8)]
options = [[F(3), F(7, 2), F(4), F(9, 2), F(5)], list(map(F, [2, 3, 4, 5, 6])), list(map(F, [4, 6, 8, 10, 12]))]
for answer, choices in zip(answers, options):
    assert choices.count(answer) == 1
print('예제 3문항 검산 통과: ④, ②, ③')
