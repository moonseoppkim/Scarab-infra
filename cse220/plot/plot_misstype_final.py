import os
import json
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from matplotlib.offsetbox import AnchoredText

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

def unit_format(value, pos):
    return f'{value} %'

def get_miss_data_by_benchmark(descriptor_data, sim_path, output_dir):
    benchmarks_org = descriptor_data["workloads_list"].copy()
    benchmarks = []
    miss_data = {}

    for benchmark in benchmarks_org:
        compulsory_miss, conflict_miss, capacity_miss, total_miss, total_hit = [], [], [], [], []
        benchmark_name = benchmark.split("/")[-1]

        for config_key in descriptor_data["configurations"].keys():
            exp_path = f"{sim_path}/{benchmark}/{descriptor_data['experiment']}/"
            file_path = f"{exp_path}{config_key}/memory.stat.0.csv"
            
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                miss_compulsory_load, miss_conflict_load, miss_capacity_load = 0, 0, 0
                miss_compulsory_store, miss_conflict_store, miss_capacity_store = 0, 0, 0
                dcache_hit, dcache_miss = 0, 0

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
                    elif line.startswith('DCACHE_MISS_count'):
                        dcache_miss = int(line.split()[-1])

                total_compulsory = miss_compulsory_load + miss_compulsory_store
                total_conflict = miss_conflict_load + miss_conflict_store
                total_capacity = miss_capacity_load + miss_capacity_store
                total_miss_val = dcache_miss
                total_hit_val = dcache_hit

            except FileNotFoundError:
                print(f"Warning: File '{file_path}' not found.")
                # Set default values if file is not found
                total_compulsory, total_conflict, total_capacity = 0, 0, 0
                total_miss_val, total_hit_val = 0, 0

            # Add data even if it's missing, so that plotting can proceed
            compulsory_miss.append(total_compulsory)
            conflict_miss.append(total_conflict)
            capacity_miss.append(total_capacity)
            total_miss.append(total_miss_val)
            total_hit.append(total_hit_val)

        miss_data[benchmark_name] = {
            'compulsory': compulsory_miss,
            'conflict': conflict_miss,
            'capacity': capacity_miss,
            'total_miss': total_miss,
            'total_hit': total_hit
        }
        benchmarks.append(benchmark_name)

    # Split benchmarks into groups and plot each group
    benchmark_groups = [benchmarks_org[:8], benchmarks_org[8:16], benchmarks_org[16:]]
    for i, benchmark_group in enumerate(benchmark_groups):
        plot_miss_data_across_benchmarks(benchmark_group, descriptor_data["configurations"], miss_data,
                                         'Dcache Miss Rate', f"{output_dir}/LAB2_group{i+1}.png")

def plot_miss_data_across_benchmarks(benchmarks, configurations, miss_data, ylabel_name, fig_name, ylim=None):
    colors = ['#800000', '#911eb4', '#4363d8', '#ff0000']  # 빨간색, 오렌지색, 파란색

    ind = np.arange(len(benchmarks))
    width = 0.12
    fig, ax = plt.subplots(figsize=(14, 6), dpi=100)

    compulsory_miss, conflict_miss, capacity_miss = {}, {}, {}

    for config_idx, config in enumerate(configurations.keys()):
        compulsory_miss[config], conflict_miss[config], capacity_miss[config] = [], [], []
        
        for benchmark in benchmarks:
            total_access = (miss_data[benchmark]['total_hit'][config_idx] +
                            miss_data[benchmark]['total_miss'][config_idx])
            miss_rate_multiplier = 100 / total_access if total_access > 0 else 0
            
            compulsory_miss[config].append(miss_data[benchmark]['compulsory'][config_idx] * miss_rate_multiplier)
            conflict_miss[config].append(miss_data[benchmark]['conflict'][config_idx] * miss_rate_multiplier)
            capacity_miss[config].append(miss_data[benchmark]['capacity'][config_idx] * miss_rate_multiplier)

    for config_idx, config in enumerate(configurations.keys()):
        bottom = np.zeros(len(benchmarks))
        ax.bar(ind + (config_idx - len(configurations) / 2) * width, compulsory_miss[config], width=width,
               label=f'{config}', color=colors[0])
        bottom += np.array(compulsory_miss[config])
        ax.bar(ind + (config_idx - len(configurations) / 2) * width, conflict_miss[config], width=width,
               bottom=bottom, color=colors[1])
        bottom += np.array(conflict_miss[config])
        ax.bar(ind + (config_idx - len(configurations) / 2) * width, capacity_miss[config], width=width,
               bottom=bottom, color=colors[2])

    ax.set_xlabel("Benchmarks", fontsize=12)
    ax.set_ylabel(ylabel_name, fontsize=12)
    ax.set_xticks(ind)
    ax.set_xticklabels(benchmarks, rotation=45, ha='right', fontsize=12)
    ax.yaxis.set_major_formatter(FuncFormatter(unit_format))

    # Adjust legend location to be closer to the top right corner
    handles = [Patch(color=colors[i], label=label) for i, label in enumerate(['Compulsory Miss', 'Conflict Miss', 'Capacity Miss'])]
    ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(1.3, 1), fontsize=12)

    plt.title("Miss Breakdown Across Benchmarks (Dcache Miss Rate %)", fontsize=14)
    ax.grid(True, axis='y', linestyle='--', color='grey')
    ax.set_ylim(0, 100)

    for i in range(1, len(benchmarks)):
        ax.axvline(x=i - 0.55, color='grey', linestyle='--')

    # Configuration Orders 텍스트 박스를 legend와 같은 높이에 배치
    config_text = "\n".join([
        "Configuration Orders:",
        "",
        "dcache_32k_assoc_4",
        "dcache_4k_assoc_1",
        "dcache_4k_assoc_4",
        "dcache_4k_assoc_64",
        "dcache_256k_assoc_1",
        "dcache_256k_assoc_4",
        "dcache_256k_assoc_64"
    ])
    fig.text(0.812, 0.75, config_text, ha='left', va='top', fontsize=10, bbox=dict(facecolor='white', edgecolor='black'))

    fig.tight_layout()
    plt.savefig(fig_name, format="png", bbox_inches="tight")


def main(output_dir, descriptor_name, simulation_path):
    descriptor_data = read_descriptor_from_json(descriptor_name)
    if descriptor_data is not None:
        get_miss_data_by_benchmark(descriptor_data, simulation_path, output_dir)

# Example usage
descriptor_filename = '/workspaces/Scarab-infra/cse220/test.json'
simulation_path = '/workspaces/Scarab-infra/seop/cse220_home/exp/simulations'
output_dir = '/workspaces/Scarab-infra/cse220/plot'

main(output_dir, descriptor_filename, simulation_path)
