from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from requests import Requests
from basicsystem import GridTopology
import numpy as np
import random


class Scheduling:
    def __init__(self, topology: GridTopology):
        self.topology = topology
        self.requests = Requests(topology)  # Initialize Requests instance

    def fifo_schedule(self, all_requests: List[Dict[str, List[Tuple[str, str, str]]]]) -> List[List[Tuple[str, int]]]:
        all_schedules = []
        for round_info in all_requests:
            schedule = []
            timeslot = 1  # Start timeslot from 1
            for request in round_info['requests']:
                request_id, _, _ = request
                schedule.append((request_id, timeslot))
                timeslot += 1
            all_schedules.append(schedule)
        return all_schedules

    def rrrn_schedule(self, all_requests: List[Dict[str, List[Tuple[str, str, str]]]], k: float, c: float, a: float) -> \
            Tuple[List[List[Tuple[str, int]]], List[List[Tuple[str, int]]]]:
        all_schedules = []
        all_pre_merge_schedules = []
        b = k + c * a  # Compute the comprehensive coefficient b

        for round_info in all_requests:
            schedule = []
            timeslot = 1  # Start timeslot from 1
            remaining_requests = round_info['requests']

            # Create a dictionary to store waiting times
            waiting_times = {request[0]: 0 for request in remaining_requests}

            # Initialize high_weight_paths for the current round
            high_weight_paths = self.requests.identify_high_weight_paths(remaining_requests,
                                                                         self.requests.find_all_shortest_paths(
                                                                             [(req[1], req[2]) for req in
                                                                              remaining_requests]))

            while remaining_requests:
                max_priority = -1
                selected_request = None
                for request_id, src, dst in remaining_requests:
                    waiting_time = waiting_times[request_id]
                    transmission_distance = self.requests.calculate_manhattan_distance(
                        self.topology.nl[int(src[1:]) - 1], self.topology.nl[int(dst[1:]) - 1])
                    priority = waiting_time / (b * transmission_distance)
                    if priority > max_priority:
                        max_priority = priority
                        selected_request = (request_id, src, dst)

                # Update waiting times for all requests
                for request in remaining_requests:
                    waiting_times[request[0]] += 1

                schedule.append((selected_request[0], timeslot))
                timeslot += 1
                remaining_requests.remove(selected_request)

            all_pre_merge_schedules.append(schedule.copy())

            # Merge requests based on high weight paths
            schedule = self.new_merge_schedule(schedule, high_weight_paths)

            all_schedules.append(schedule)
        return all_schedules, all_pre_merge_schedules

    def new_merge_schedule(self, schedule: List[Tuple[str, int]],
                           high_weight_paths: Dict[str, Tuple[List[str], List[str]]]) -> List[Tuple[str, int]]:
        num_requests = len(schedule)
        merged_schedule = schedule.copy()

        # Collect all high weight paths for each request
        selected_paths = {}
        for request_id in high_weight_paths:
            path1, path2 = high_weight_paths[request_id]
            selected_paths[request_id] = [path1, path2]
            # Display the high weight paths for each request
            print(
                f"Request {request_id} high weight paths: {', '.join([' -> '.join(path) for path in selected_paths[request_id] if path])}")

        # Attempt to merge requests starting from the last one
        for i in range(num_requests - 1, -1, -1):
            request_a_id, timeslot_a = merged_schedule[i]
            paths_a = selected_paths[request_a_id]
            merged = False

            for j in range(timeslot_a - 1):
                if j + 1 in [ts for _, ts in merged_schedule]:
                    timeslot_b_requests = [req_id for req_id, ts in merged_schedule if ts == j + 1]
                    conflict = False
                    for request_b_id in timeslot_b_requests:
                        paths_b = selected_paths[request_b_id]
                        if self.all_paths_conflict(paths_a, paths_b):
                            conflict = True
                            break
                    if not conflict:
                        merged_schedule[i] = (request_a_id, j + 1)
                        merged = True
                        break

            # If not merged, keep in its original timeslot
            if not merged:
                merged_schedule[i] = (request_a_id, timeslot_a)

        # Reorganize schedule to eliminate empty timeslots
        final_schedule = []
        timeslot_mapping = {}
        current_timeslot = 1
        for request_id, timeslot in merged_schedule:
            if timeslot not in timeslot_mapping:
                timeslot_mapping[timeslot] = current_timeslot
                current_timeslot += 1
            final_schedule.append((request_id, timeslot_mapping[timeslot]))

        final_schedule = sorted(final_schedule, key=lambda x: x[1])
        return final_schedule

    def fifo_merge(self, fifo_schedule: List[Tuple[str, int]],
                   all_requests: List[Dict[str, List[Tuple[str, str, str]]]]) -> List[Tuple[str, int]]:
        merged_schedule = []
        timeslot = 1

        # Create a mapping of request IDs to their paths and assign priorities based on path length
        request_paths = {}
        for round_info in all_requests:
            for request in round_info['requests']:
                request_id = request[0]
                src, dst = request[1], request[2]
                # Find all paths for this request
                paths = self.requests.find_all_shortest_paths([(src, dst)])
                # Sort paths by length to determine priority (shorter paths have higher priority)
                request_paths[request_id] = sorted(paths[(src, dst)], key=lambda p: len(p))

        while fifo_schedule:
            current_timeslot_requests = []
            remaining_requests = []

            for i in range(len(fifo_schedule)):
                request_a_id, _ = fifo_schedule[i]
                paths_a = request_paths[request_a_id]

                conflict = False
                priority_mismatch = False

                for existing_request_id in current_timeslot_requests:
                    paths_b = request_paths[existing_request_id]

                    # 检查路径冲突
                    if self.all_paths_conflict(paths_a, paths_b):
                        conflict = True
                        break

                    # 优先级判定：如果当前请求的路径长度明显大于已合并请求的路径长度，不合并
                    if len(paths_a[0]) > len(paths_b[0]) * 1.2:
                        priority_mismatch = True
                        break

                if not conflict and not priority_mismatch:
                    current_timeslot_requests.append(request_a_id)
                else:
                    remaining_requests.append(fifo_schedule[i])

            # Assign the current timeslot to all non-conflicting requests
            for request_id in current_timeslot_requests:
                merged_schedule.append((request_id, timeslot))

            # Move to the next timeslot
            timeslot += 1
            fifo_schedule = remaining_requests

        # Sort the merged schedule by timeslot
        final_schedule = sorted(merged_schedule, key=lambda x: x[1])
        return final_schedule

    def all_paths_conflict(self, paths_a: List[List[str]], paths_b: List[List[str]]) -> bool:
        for path_a in paths_a:
            for path_b in paths_b:
                if path_a and path_b and self.paths_conflict(path_a, path_b):
                    return True
        return False

    def paths_conflict(self, path1: List[str], path2: List[str]) -> bool:
        return bool(set(path1) & set(path2))

    def plot_first_round_schedule(self, first_round_schedule: List[Tuple[str, int]], title: str, total_timeslots: int):
        # Plot the first round schedule with customized x-axis
        fig, ax = plt.subplots(figsize=(12, 8))  # Increase figure size
        x = [timeslot for _, timeslot in first_round_schedule]
        y = [i * 1.2 for i in range(len(first_round_schedule))]  # Increase the distance between points
        labels = [req_id.replace("Round 1 Request", "req") for req_id, _ in first_round_schedule]

        ax.scatter(x, y)
        for i, label in enumerate(labels):
            ax.annotate(label, (x[i] + 0.2, y[i]))  # Shift labels slightly to the right

        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.xaxis.set_major_formatter('{x:.0f}')
        plt.xticks(np.arange(1, total_timeslots + 1, 1))

        plt.xlabel('Timeslots')
        plt.ylabel('Requests')
        plt.title(title)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.savefig(f"{title}.png", dpi=600)
        plt.show()

    def display_schedule(self, all_schedules: List[List[Tuple[str, int]]], schedule_type: str):
        # Display the schedule
        print(f"{schedule_type} Schedule:")
        for round_number, schedule in enumerate(all_schedules, start=1):
            print(f"Round {round_number}:")
            for request_id, timeslot in schedule:
                print(f"  {request_id} -> Timeslot {timeslot}")
        print()

    def calculate_manhattan_distance(self, node1, node2):
        index1 = int(node1.name[1:]) - 1
        index2 = int(node2.name[1:]) - 1
        row1, col1 = divmod(index1, self.topology.size)
        row2, col2 = divmod(index2, self.topology.size)
        return abs(row1 - row2) + abs(col1 - col2)

    def generate_failure_nodes(self, num_nodes: int, num_timeslots: int, failure_probability: float) -> Dict[
        int, List[int]]:
        """
        Generate a dictionary of failure nodes for each timeslot based on the failure probability.
        The failure_probability is used to determine the fraction of timeslots and the fraction of nodes that fail.
        """
        failure_nodes = {}
        num_failed_timeslots = max(1, int(num_timeslots * failure_probability))  # Ensure at least one timeslot fails
        failed_timeslots = np.random.choice(range(1, num_timeslots + 1), num_failed_timeslots, replace=False)

        for timeslot in failed_timeslots:
            num_failed_nodes = max(1, int(num_nodes * failure_probability))  # Ensure at least one node fails
            failed_nodes = np.random.choice(range(1, num_nodes + 1), num_failed_nodes, replace=False).tolist()
            failure_nodes[timeslot] = failed_nodes

        return failure_nodes

    def check_requests_failures(self, schedule: List[Tuple[str, int]],
                                high_weight_paths: Dict[str, Tuple[List[str], List[str]]],
                                failure_nodes: Dict[int, List[int]]) -> List[str]:
        """
        Check which requests in the schedule have paths that include failure nodes.
        """
        failed_requests = []
        for request_id, timeslot in schedule:
            paths = high_weight_paths[request_id]
            failed_nodes = failure_nodes.get(timeslot, [])
            all_paths_fail = all(any(int(node[1:]) in failed_nodes for node in path) for path in paths)
            if all_paths_fail:
                failed_requests.append(request_id)
        return failed_requests

    def check_failures_across_schedules(self, schedules: Dict[str, List[Tuple[str, int]]],
                                        high_weight_paths: Dict[str, Tuple[List[str], List[str]]],
                                        failure_nodes: Dict[int, List[int]]) -> Dict[str, Dict[int, List[str]]]:
        """
        Check failures across multiple schedules and return a dictionary of failed requests per schedule type.
        """
        all_failed_requests = {}
        for schedule_name, schedule in schedules.items():
            failed_requests_by_timeslot = {}
            for timeslot, nodes in failure_nodes.items():
                failed_requests_by_timeslot[timeslot] = []
                for request_id, ts in schedule:
                    if ts == timeslot:
                        paths = high_weight_paths[request_id]
                        all_paths_fail = all(any(int(node[1:]) in nodes for node in path) for path in paths)
                        if all_paths_fail:
                            failed_requests_by_timeslot[timeslot].append(request_id)
                if not failed_requests_by_timeslot[timeslot]:
                    failed_requests_by_timeslot[timeslot].append(f"{schedule_name}在这个时隙无requests")
            all_failed_requests[schedule_name] = failed_requests_by_timeslot
        return all_failed_requests

    def calculate_total_delay(self, schedule: List[Tuple[str, int]]) -> int:
        """
        Calculate the total delay for a given schedule.
        """
        delay = 0
        timeslot_counts = {}
        for _, timeslot in schedule:
            if timeslot not in timeslot_counts:
                timeslot_counts[timeslot] = 0
            timeslot_counts[timeslot] += 1

        for timeslot, count in timeslot_counts.items():
            delay += sum([timeslot - 1] * count)

        return delay

    def extract_timeslot_request_info(self, fifo_merged_schedule: List[Tuple[str, int]], collected_requests: List[Tuple[int, Tuple[str, str, str]]]) -> Dict[int, List[Tuple[str, int]]]:
        """
        Extracts information about which requests are in each timeslot and their Manhattan distances.

        Args:
            fifo_merged_schedule (List[Tuple[str, int]]): The result of the FIFO Merge scheduling algorithm,
                which contains the requests and their assigned timeslots.
            collected_requests (List[Tuple[int, Tuple[str, str, str]]]): List of collected requests with round number, request ID, source, and destination.

        Returns:
            Dict[int, List[Tuple[str, int]]]: A dictionary where the key is the timeslot number and the value is a list of
                tuples, each containing a request ID and its Manhattan distance.
        """
        # Create a dictionary to store requests for each timeslot
        timeslot_request_info = {}

        # Create a mapping from request IDs to their corresponding src and dst nodes
        request_info_map = {req[1][0]: req[1] for req in collected_requests}

        # Iterate over the FIFO_Merge schedule to extract requests and their timeslots
        for request_id, timeslot in fifo_merged_schedule:
            # Find the corresponding request in the collected requests list
            if request_id in request_info_map:
                req_id, src, dst = request_info_map[request_id]

                # Calculate Manhattan distance between source and destination nodes
                src_node = self.topology.nl[int(src[1:]) - 1]
                dst_node = self.topology.nl[int(dst[1:]) - 1]
                manhattan_distance = self.requests.calculate_manhattan_distance(src_node, dst_node)

                # Add the request ID and Manhattan distance to the corresponding timeslot in the dictionary
                if timeslot not in timeslot_request_info:
                    timeslot_request_info[timeslot] = []
                timeslot_request_info[timeslot].append((req_id, manhattan_distance))

        return timeslot_request_info

    def check_decoherence(self, timeslot_request_info: Dict[int, List[Tuple[str, int]]], nodes_number: int,
                          decoherence_rate: float) -> int:
        """
        Check which requests in each timeslot decohere based on their Manhattan distances and the decoherence rate.

        Args:
            timeslot_request_info (Dict[int, List[Tuple[str, int]]]): A dictionary with timeslot number as the key
                and a list of tuples containing request ID and Manhattan distance as the value.
            nodes_number (int): The number of nodes in the grid network.
            decoherence_rate (float): The decoherence rate used in the decoherence probability formula.

        Returns:
            int: The total number of decohered requests.
        """
        size = int(np.sqrt(nodes_number))
        longest_shortest_path = 2 * (size - 1)
        decohered_requests_count = 0

        for timeslot, requests in timeslot_request_info.items():
            for request_id, manhattan_distance in requests:
                # Calculate the decoherence probability
                length_ratio = manhattan_distance / longest_shortest_path
                # decoherence_probability = 1 - np.exp(-decoherence_rate * length_ratio) 用删井
                decoherence_probability = 1 - np.exp(-decoherence_rate)

                # Determine if the request decoheres
                if random.random() < decoherence_probability:
                    decohered_requests_count += 1
                    print(
                        f"Request {request_id} in timeslot {timeslot} decohered with probability {decoherence_probability:.4f}")

        return decohered_requests_count
