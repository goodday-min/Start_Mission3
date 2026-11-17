# -*- coding: utf-8 -*-
"""
Mini NPU 시뮬레이터 (1~8단계: 메뉴 + 모드 1 + 모드 2 판정 + 성능 분석 + 결과 요약)

MACEngine    : 계산 담당 (MAC 연산, 점수 비교, 시간 측정)
DataManager  : 데이터 담당 (표 저장/읽기, 입력 받기, 라벨 통일)
NPUSimulator : 진행 담당 (메뉴와 모드 흐름)
"""

import json
import time


class MACEngine:
    # 두 점수의 차이가 이 값보다 작으면 동점으로 본다 (소수 계산 오차 대비)
    EPSILON = 1e-9

    def mac(self, pattern_list, filter_list):
        """같은 자리끼리 곱해서 모두 더한 점수를 돌려준다."""
        n = len(pattern_list)
        total = 0.0
        # 모든 칸(n x n)을 하나씩 돈다 -> 계산 횟수 N² (시간 복잡도 O(N²)의 근거)
        for row in range(n):
            for col in range(n):
                # MAC: 같은 자리끼리 곱하고(M) 통에 쌓는다(A)
                total += pattern_list[row][col] * filter_list[row][col]
        return total

    def compare_scores(self, score_a, score_b):
        """'A', 'B', 'TIE'(동점) 중 하나를 돌려준다."""
        # 차이가 아주 작으면 동점 (소수 오차 때문에 == 비교는 위험)
        if abs(score_a - score_b) < self.EPSILON:
            return "TIE"
        if score_a > score_b:
            return "A"
        return "B"

    def measure_time(self, pattern_list, filter_list, repeat=10):
        """mac() 을 repeat 번 실행해서 1회 평균 시간(ms)을 돌려준다."""
        total_seconds = 0.0
        for i in range(repeat):
            # 스톱워치 시작 (mac() 호출 구간만 잰다, 입출력 시간 제외)
            start = time.perf_counter()
            self.mac(pattern_list, filter_list)
            total_seconds += time.perf_counter() - start
        # 평균(초)을 ms 로 바꿔서 돌려준다
        return total_seconds / repeat * 1000




class DataManager:
    # 데이터에 적힌 값(대문자로 바꿔서 찾음) -> 표준 라벨
    LABEL_TABLE = {"+": "Cross", "CROSS": "Cross", "X": "X"}

    def __init__(self):
        self.matrix_dict = {}    # 이름표를 붙여 표를 보관하는 곳

    def store_matrix(self, name, matrix_list):
        self.matrix_dict[name] = matrix_list

    def get_matrix(self, name):
        return self.matrix_dict[name]

    def get_value(self, name, row, col):
        return self.matrix_dict[name][row][col]

    def set_value(self, name, row, col, value):
        self.matrix_dict[name][row][col] = value

    def parse_row(self, line, size):
        """'1 0 1' 같은 글자를 [1.0, 0.0, 1.0] 로 바꾼다. 잘못되면 ValueError."""
        token_list = line.split()
        # 칸 개수 검사 (입력 검증)
        if len(token_list) != size:
            raise ValueError("열 개수 불일치")
        row_list = []
        for token in token_list:
            row_list.append(float(token))    # 숫자가 아니면 여기서 ValueError
        return row_list



    def input_matrix(self, title, size=3):
        """size 줄을 입력받아 표로 돌려준다. 틀린 줄은 다시 입력받는다."""
        print("%s (%d줄 입력, 공백 구분)" % (title, size))
        matrix_list = []
        # 필요한 줄 수가 찰 때까지 반복 (틀린 줄은 다시 입력)
        while len(matrix_list) < size:
            line = input()
            try:
                matrix_list.append(self.parse_row(line, size))
            except ValueError:
                print("입력 형식 오류: 각 줄에 %d개의 숫자를 공백으로 구분해 입력하세요." % size)
        return matrix_list


    def load_json(self, path):
        """JSON 파일을 읽어서 딕셔너리로 돌려준다."""
        with open(path, encoding="utf-8") as file:
            # JSON 글자 -> 파이썬 딕셔너리
            return json.load(file)


    def load_filters(self, filter_dict):
        """filters 부분을 읽어 'size_5_Cross' 같은 이름표로 보관한다."""
        for size_key, label_dict in filter_dict.items():
            label_list = []
            for label_key, matrix_list in label_dict.items():
                # 필터 이름 cross/x -> 표준 라벨 Cross/X
                label = self.normalize_label(label_key)
                # 예: size_5 + Cross -> "size_5_Cross"
                self.store_matrix(size_key + "_" + label, matrix_list)
                label_list.append(label)
            print("%s 필터 로드 완료 (%s)" % (size_key, ", ".join(label_list)))

    def extract_size(self, key):
        """'size_13_1' 에서 13 을 꺼낸다. 형식이 다르면 ValueError."""
        part_list = key.split("_")
        # "size_13_1" 을 _ 로 쪼개 크기(13)를 꺼낸다
        if len(part_list) != 3 or part_list[0] != "size" or not part_list[1].isdigit():
            raise ValueError("키 형식 오류: %s" % key)
        return int(part_list[1])

    def check_size(self, pattern_list, filter_list):
        """패턴과 필터가 같은 크기의 정사각형인지 확인한다. 아니면 ValueError."""
        size = len(pattern_list)
        # 패턴과 필터 크기 일치 검증 (불일치 -> 케이스 FAIL)
        if len(filter_list) != size:
            raise ValueError("크기 불일치: 패턴 %d줄, 필터 %d줄" % (size, len(filter_list)))
        for row_list in pattern_list + filter_list:
            if len(row_list) != size:
                raise ValueError("크기 불일치: 정사각형 표가 아닙니다.")

    def normalize_label(self, raw):
        """'+', 'cross', 'x' 등을 'Cross' 또는 'X' 로 바꾼다."""
        # 공백 제거 + 대문자로 통일해서 번역표에서 찾는다
        key = str(raw).strip().upper()
        # 번역표에 없으면 오류 -> 그 케이스만 FAIL 처리된다
        if key not in self.LABEL_TABLE:
            raise ValueError("알 수 없는 라벨: %r" % (raw,))
        return self.LABEL_TABLE[key]















class NPUSimulator:
    # data.json 에 3x3 자료가 없어서, 성능 측정용으로 쓰는 3x3 십자가 예시
    SAMPLE_3X3 = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]

    def __init__(self):
        self.macengine = MACEngine()
        self.datamanager = DataManager()

    def run(self):
        print("=== Mini NPU Simulator ===")
        while True:
            print("[모드 선택]")
            print("1. 사용자 입력 (3x3)")
            print("2. data.json 분석")
            choice = input("선택: ").strip()
            if choice == "1":
                self.run_mode1()
                break
            elif choice == "2":
                self.run_mode2()
                break
            else:
                print("입력 형식 오류: 1 또는 2 를 입력하세요.")

    def run_mode1(self):
        print("[1] 필터 입력")
        self.datamanager.store_matrix("A", self.datamanager.input_matrix("필터 A"))
        self.datamanager.store_matrix("B", self.datamanager.input_matrix("필터 B"))
        print("필터 A, B 저장 완료")

        print("[2] 패턴 입력")
        self.datamanager.store_matrix("PATTERN", self.datamanager.input_matrix("패턴"))
        print("패턴 저장 완료")

        pattern_list = self.datamanager.get_matrix("PATTERN")
        score_a = self.macengine.mac(pattern_list, self.datamanager.get_matrix("A"))
        score_b = self.macengine.mac(pattern_list, self.datamanager.get_matrix("B"))
        avg_ms = self.macengine.measure_time(pattern_list, self.datamanager.get_matrix("A"))
        result = self.macengine.compare_scores(score_a, score_b)

        print("[3] MAC 결과")
        print("A 점수:", score_a)
        print("B 점수:", score_b)
        print("연산 시간(평균/10회): %.3f ms" % avg_ms)
        if result == "TIE":
            print("판정: 판정 불가 (|A-B| < %g)" % self.macengine.EPSILON)
        else:
            print("판정:", result)

        self.print_performance([[pattern_list, self.datamanager.get_matrix("A")]])



    def run_mode2(self):
        print("[1] 필터 로드")
        try:
            # 파일 문제는 안내 후 종료 (프로그램이 꺼지지 않게)
            data_dict = self.datamanager.load_json("data.json")
            filter_dict = data_dict["filters"]
            self.datamanager.load_filters(filter_dict)
            pattern_dict = data_dict["patterns"]
        except (OSError, ValueError, KeyError) as error:
            print("data.json 을 불러올 수 없습니다:", error)
            return

        print("[2] 패턴 분석")
        fail_list = []    # 실패한 케이스를 "케이스 이름: 사유" 글자로 모아 둠
        # 케이스마다 따로 try: 하나가 실패해도 다음 케이스를 계속한다
        for key, case_dict in pattern_dict.items():
            print("---", key, "---")
            try:
                reason = self.analyze_pattern(key, case_dict)    # PASS 면 ""
            except ValueError as error:
                reason = "데이터 문제: %s" % error
                print("FAIL (%s)" % reason)
            except KeyError as error:
                reason = "데이터 문제: 필요한 항목이 없습니다 %s" % error
                print("FAIL (%s)" % reason)
            except TypeError:
                reason = "데이터 문제: 값의 형식이 올바르지 않습니다"
                print("FAIL (%s)" % reason)
            if reason != "":
                fail_list.append("%s: %s" % (key, reason))

        # 성능 측정용 [패턴 표, 필터 표] 목록 (3x3 은 예시 사용)
        case_list = [[self.SAMPLE_3X3, self.SAMPLE_3X3]]
        try:
            for size_key in filter_dict:
                cross_list = self.datamanager.get_matrix(size_key + "_Cross")
                case_list.append([cross_list, cross_list])
        except KeyError as error:
            print("성능 분석에 필요한 필터가 없습니다:", error)
        self.print_performance(case_list)

        print("[4] 결과 요약")
        # 통과 수 = 총 수 - 실패 수
        total_count = len(pattern_dict)
        print("총 테스트: %d개" % total_count)
        print("통과: %d개" % (total_count - len(fail_list)))
        print("실패: %d개" % len(fail_list))
        if len(fail_list) > 0:
            print("실패 케이스:")
            for fail in fail_list:
                print("-", fail)



    def analyze_pattern(self, key, case_dict):
        """패턴 1개를 판정하고 PASS/FAIL 을 출력한다. 실패 사유를 돌려준다(PASS 면 빈 글자)."""
        # 키에서 N 추출 -> 같은 크기의 필터를 고른다
        size = self.datamanager.extract_size(key)
        pattern_list = case_dict["input"]
        cross_list = self.datamanager.get_matrix("size_%d_Cross" % size)
        x_list = self.datamanager.get_matrix("size_%d_X" % size)
        # 크기 불일치면 ValueError (비정상 종료 방지)
        self.datamanager.check_size(pattern_list, cross_list)
        self.datamanager.check_size(pattern_list, x_list)

        # 같은 패턴을 Cross 필터, X 필터에 각각 MAC
        cross_score = self.macengine.mac(pattern_list, cross_list)
        x_score = self.macengine.mac(pattern_list, x_list)
        # epsilon 기준 비교: A(Cross) / B(X) / TIE(동점)
        result = self.macengine.compare_scores(cross_score, x_score)
        # A -> Cross, B -> X, 동점 -> UNDECIDED
        judge = {"A": "Cross", "B": "X", "TIE": "UNDECIDED"}[result]
        # 정답도 표준 라벨로 통일한 뒤 비교한다
        expected = self.datamanager.normalize_label(case_dict["expected"])

        # 표준 라벨끼리 비교 -> PASS / FAIL
        if judge == expected:
            status = "PASS"
            reason = ""
        elif judge == "UNDECIDED":
            status = "FAIL (동점 규칙)"
            reason = "동점(UNDECIDED) 처리 규칙에 따라 FAIL"
        else:
            status = "FAIL"
            reason = "판정 %s 와 expected %s 불일치" % (judge, expected)
        print("Cross 점수:", cross_score)
        print("X 점수:", x_score)
        print("판정: %s | expected: %s | %s" % (judge, expected, status))
        return reason

    def print_performance(self, case_list):
        """case_list 의 [패턴 표, 필터 표] 마다 MAC 시간을 재서 표로 출력한다."""
        print("[성능 분석] (평균/10회)")
        print("크기\t평균 시간(ms)\t연산 횟수")
        for case in case_list:
            pattern_list = case[0]
            filter_list = case[1]
            size = len(pattern_list)
            avg_ms = self.macengine.measure_time(pattern_list, filter_list)
            # 연산 횟수 = N x N
            print("%dx%d\t%.3f\t\t%d" % (size, size, avg_ms, size * size))


if __name__ == "__main__":
    NPUSimulator().run()
