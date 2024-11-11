import os
import json
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

matplotlib.rc('font', size=14)

def read_descriptor_from_json(descriptor_filename):
    # JSON 파일에서 descriptor 데이터를 읽어들임
    try:
        with open(descriptor_filename, 'r') as json_file:
            descriptor_data = json.load(json_file)
        return descriptor_data
    except FileNotFoundError:
        print(f"Error: File '{descriptor_filename}' not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON in file '{descriptor_filename}': {e}")
        return None

def get_miss_data_by_benchmark(descriptor_data, sim_path, output_dir):
    benchmarks_org = descriptor_data["workloads_list"].copy()
    benchmarks = []
    miss_data = {}

    try:
        for benchmark in benchmarks_org:
            compulsory_miss, conflict_miss, capacity_miss, total_miss, total_hit = [], [], [], [], []
            benchmark_name = benchmark.split("/")

            for config_key in descriptor_data["configurations"].keys():
                exp_path = f"{sim_path}/{benchmark}/{descriptor_data['experiment']}/"
                file_path = f"{exp_path}{config_key}/memory.stat.0.csv"
                
                # 파일 열기 및 데이터 읽기
                try:
                    with open(file_path, 'r') as f:
                        lines = f.readlines()
                except FileNotFoundError:
                    print(f"Warning: File '{file_path}' not found.")
                    continue

                miss_compulsory_load, miss_conflict_load, miss_capacity_load = 0, 0, 0
                miss_compulsory_store, miss_conflict_store, miss_capacity_store = 0, 0, 0
                dcache_hit, dcache_miss = 0, 0

                # 각 miss 타입의 데이터를 읽음
                for line in lines:
                    line = line.strip()
                    if line.startswith('DCACHE_MISS_COMPULSORY_LOAD_count'):
                        miss_compulsory_load = int(line.split()[-1])
                    elif line.startswith('DCACHE_MISS_CONFLICT_LOAD_count'):
                        miss_conflict_load = int(line.split()[-1])
                    elif line.startswith('DCACHE_MISS_CAPACITY_LOAD_count'):
                        miss_capacity_load = int(line.split()[-1])
                    elif line.startswith('DCACHE_MISS_COMPULSORY_STORE_count'):
                        miss_compulsory_store = int(line.split()[-1])
                    elif line.startswith('DCACHE_MISS_CONFLICT_STORE_count'):
                        miss_conflict_store = int(line.split()[-1])
                    elif line.startswith('DCACHE_MISS_CAPACITY_STORE_count'):
                        miss_capacity_store = int(line.split()[-1])
                    elif line.startswith('DCACHE_HIT_count'):
                        dcache_hit = int(line.split()[-1])
                        break
                    elif line.startswith('DCACHE_MISS_count'):
                        dcache_miss = int(line.split()[-1])

                total_compulsory = miss_compulsory_load + miss_compulsory_store
                total_conflict = miss_conflict_load + miss_conflict_store
                total_capacity = miss_capacity_load + miss_capacity_store
                total_miss_val = dcache_miss
                total_hit_val = dcache_hit

                compulsory_miss.append(total_compulsory)
                conflict_miss.append(total_conflict)
                capacity_miss.append(total_capacity)
                total_miss.append(total_miss_val)
                total_hit.append(total_hit_val)

            miss_data[benchmark] = {
                'compulsory': compulsory_miss,
                'conflict': conflict_miss,
                'capacity': capacity_miss,
                'total_miss': total_miss,
                'total_hit': total_hit
            }

            benchmarks.append(benchmark_name)

        # 각 benchmark마다 그래프 생성
        for benchmark_name in benchmarks:
            miss_data_subset = miss_data[benchmark_name[0]]
            plot_miss_data_with_stacked_counts(
                benchmark_name[0],
                descriptor_data["configurations"],
                miss_data_subset,
                'Miss Rate Proportion',
                f"{output_dir}/1024LAB2_{benchmark_name[0]}_MissRate.png"
            )

    except Exception as e:
        print(f"Exception occurred: {e}")

def plot_miss_data_with_stacked_counts(benchmark, configurations, miss_data, ylabel_name, fig_name, ylim=None):
    colors = ['#800000', '#911eb4', '#4363d8', '#ff0000']  # Colors for compulsory, conflict, capacity, and total dcache miss
    ind = np.arange(len(configurations))  # x locations for configurations
    width = 0.35
    fig, ax = plt.subplots(figsize=(16, 6), dpi=100)  # 그래프 크기 조정

    compulsory_ratio = []
    conflict_ratio = []
    capacity_ratio = []
    total_miss_ratio = []  # 전체 miss rate

    # 각 configuration에서 miss 비율을 계산
    for idx in range(len(configurations)):
        total_miss = miss_data['total_miss'][idx]
        total_hit = miss_data['total_hit'][idx]
        total_access = total_miss + total_hit

        # 전체 miss rate를 계산 (miss / 전체 access)
        if total_access > 0:
            miss_rate = total_miss / total_access
        else:
            miss_rate = 0  # access가 없을 경우 miss rate를 0으로 설정
        total_miss_ratio.append(miss_rate)

        # 각 miss 유형의 비율 계산 (total_miss가 0일 때는 비율을 0으로 설정)
        if total_miss > 0:
            compulsory_ratio.append(miss_data['compulsory'][idx] / total_miss)
            conflict_ratio.append(miss_data['conflict'][idx] / total_miss)
            capacity_ratio.append(miss_data['capacity'][idx] / total_miss)
        else:
            compulsory_ratio.append(0)
            conflict_ratio.append(0)
            capacity_ratio.append(0)

    # Stacked bar plot for miss types
    p1 = ax.bar(ind, compulsory_ratio, width, label='Compulsory Miss', color=colors[0])
    p2 = ax.bar(ind, conflict_ratio, width, bottom=compulsory_ratio, label='Conflict Miss', color=colors[1])
    p3 = ax.bar(ind, capacity_ratio, width, bottom=np.array(compulsory_ratio) + np.array(conflict_ratio), label='Capacity Miss', color=colors[2])

    # 각 bar 옆에 miss 개수를 텍스트로 추가 (세로로 쌓아 올리는 방식)
    spacing = 0.05  # 막대 오른쪽으로 텍스트를 얼마나 띄울지 설정
    for idx in range(len(configurations)):
        cumulative_height = 0.02  # 쌓이는 위치를 계산하기 위해 사용
        # compulsory miss 텍스트 블럭 쌓기
        ax.text(ind[idx] + width + spacing, cumulative_height, f'{miss_data["compulsory"][idx]}',
                ha='center', va='center', color=colors[0], fontweight='bold', fontsize=10)
        cumulative_height += spacing

        # conflict miss 텍스트 블럭 쌓기
        ax.text(ind[idx] + width + spacing, cumulative_height, f'{miss_data["conflict"][idx]}',
                ha='center', va='center', color=colors[1], fontweight='bold', fontsize=10)
        cumulative_height += spacing

        # capacity miss 텍스트 블럭 쌓기
        ax.text(ind[idx] + width + spacing, cumulative_height, f'{miss_data["capacity"][idx]}',
                ha='center', va='center', color=colors[2], fontweight='bold', fontsize=10)
        cumulative_height += spacing

        # total dcache miss 텍스트 블럭 쌓기 (빨간색)
        ax.text(ind[idx] + width + spacing, cumulative_height, f'{miss_data["total_miss"][idx]}',
                ha='center', va='center', color=colors[3], fontweight='bold', fontsize=10)

    ax.set_xlabel("Configurations", fontsize=12)
    ax.set_ylabel(ylabel_name, fontsize=12)
    ax.set_xticks(ind)
    ax.set_xticklabels(configurations.keys(), rotation=27, ha='right', fontsize=12)
    ax.grid('x')

    # 강제로 legend 항목을 수동으로 추가
    handles = [
        Patch(color=colors[3], label='Total Dcache Miss'),
        Patch(color=colors[2], label='Capacity Miss'),
        Patch(color=colors[1], label='Conflict Miss'),
        Patch(color=colors[0], label='Compulsory Miss'),
    ]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.05, 1), borderaxespad=0., fontsize=12)

    plt.title(f"Miss Breakdown for Benchmark: {benchmark}", fontsize=14)

    # Y-axis limit을 조정하여 작은 값들이 잘 보이게 함
    ax.set_ylim(0, 1.05)

    fig.tight_layout()
    plt.savefig(fig_name, format="png", bbox_inches="tight")


def main(output_dir, descriptor_name, simulation_path):
    descriptor_data = read_descriptor_from_json(descriptor_name)
    if descriptor_data is not None:
        get_miss_data_by_benchmark(descriptor_data, simulation_path, output_dir)

# 파일 경로 설정
descriptor_filename = '/workspaces/Scarab-infra/cse220/test.json'#args.descriptor_name
simulation_path = '/workspaces/Scarab-infra/seop/cse220_home/exp/simulations'
output_dir = '/workspaces/Scarab-infra/cse220/plot'

main(output_dir, descriptor_filename, simulation_path)
