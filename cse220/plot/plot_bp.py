import os
import string
import json
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rc('font', size=14)

def read_descriptor_from_json(descriptor_filename):
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

def get_BP(descriptor_data, sim_path, output_dir):
    benchmarks_org = descriptor_data["workloads_list"].copy()
    benchmarks = []
    bp = {}

    try:
        for config_key in descriptor_data["configurations"].keys():
            bp_config = []
            avg_BP_config = 0.0
            cnt_benchmarks = 0

            for benchmark in benchmarks_org:
                benchmark_name = benchmark.split("/")[-1]
                exp_path = os.path.join(sim_path, benchmark, descriptor_data["experiment"])
                BP = 0

                try:
                    with open(os.path.join(exp_path, config_key, 'bp.stat.0.csv')) as f:
                        lines = f.readlines()
                        for line in lines:
                            if 'BP_ON_PATH_MISPREDICT_pct' in line:
                                tokens = [x.strip() for x in line.split(',')]
                                BP = float(tokens[1])
                                break
                except FileNotFoundError:
                    BP = 0

                avg_BP_config += BP
                cnt_benchmarks += 1

                if len(benchmarks_org) > len(benchmarks):
                    benchmarks.append(benchmark_name)

                bp_config.append(BP)

            if cnt_benchmarks > 0:
                bp_config.append(avg_BP_config / cnt_benchmarks)
            else:
                bp_config.append(0)  # Handle case where there are no benchmarks

            bp[config_key] = bp_config

        # 'Avg' 추가된 벤치마크 리스트 생성
        benchmarks.append('Avg')
        fig_name = get_unique_filename(output_dir, 'FigureA.png')
        bp_data(benchmarks, bp, 'Misprediction', fig_name)  # 수정된 benchmarks 리스트 전달

    except Exception as e:
        print(f"An error occurred: {e}")


def get_unique_filename(directory, base_name):
    base, ext = os.path.splitext(base_name)
    file_name = base_name

    # Check for 'A' to 'Z'
    for suffix in [''] + list(string.ascii_uppercase):
        file_name = os.path.join(directory, f"{base}{suffix}{ext}")
        if not os.path.exists(file_name):
            return file_name

    # If 'A' to 'Z' are taken, continue with 'AA', 'AB', etc.
    for first_letter in string.ascii_uppercase:
        for second_letter in string.ascii_uppercase:
            suffix = first_letter + second_letter
            file_name = os.path.join(directory, f"{base}{suffix}{ext}")
            if not os.path.exists(file_name):
                return file_name

    return file_name

def bp_data(benchmarks, data, ylabel_name, fig_name, ylim=None):
    print(data)
    # 확장된 색상 리스트로 최대 10개의 항목 지원
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

    ind = np.arange(len(benchmarks))
    num_configs = min(len(data.keys()), 10)  # 최대 10개의 항목까지 지원
    width = 0.8 / num_configs  # 막대의 너비를 조정하여 10개의 항목이 잘 맞도록 함

    fig, ax = plt.subplots(figsize=(14, 4.4), dpi=80)

    keys = list(data.keys())[:10]  # 최대 10개의 항목만 선택
    for idx, key in enumerate(keys):
        ax.bar(ind + (idx * width), data[key], width=width, color=colors[idx], edgecolor='black', label=key)

    ax.set_xlabel("Benchmarks")
    ax.set_ylabel(ylabel_name)
    ax.set_xticks(ind + width * (num_configs / 2))
    ax.set_xticklabels(benchmarks, rotation=27, ha='right')
    ax.grid(axis='x')
    
    # Y축을 0에서 25로 고정
    ax.set_ylim(0, 30)

    # Legend를 우측 상단 구석으로 이동
    ax.legend(loc="upper right", bbox_to_anchor=(1, 1), fontsize=10)

    fig.tight_layout()
    plt.savefig(fig_name, format="png", bbox_inches="tight")


def main(output_dir, descriptor_name, simulation_path):
    descriptor_data = read_descriptor_from_json(descriptor_name)
    if descriptor_data is not None:
        get_BP(descriptor_data, simulation_path, output_dir)

# 파일 경로 설정
descriptor_filename = '/workspaces/Scarab-infra/cse220/test.json'
simulation_path = '/workspaces/Scarab-infra/seop/cse220_home/exp/simulations'
output_dir = '/workspaces/Scarab-infra/cse220/plot'

main(output_dir, descriptor_filename, simulation_path)
