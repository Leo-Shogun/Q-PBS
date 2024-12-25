from basicsystem import GridTopology
from qns.entity.node.app import Application
from requests import Requests
from scheduling import Scheduling
import numpy as np
import sys

def main():
    # Redirect all print statements to a file
    with open("output.txt", "w", encoding="utf-8") as f:
        sys.stdout = f

        nodes_number = 36
        nodes_apps = [Application()] * nodes_number  # Example list of applications
        qchannel_args = {}  # Example quantum channel arguments
        cchannel_args = {}  # Example classical channel arguments
        memory_args = {}  # Example memory arguments

        grid_topology = GridTopology(nodes_number, nodes_apps, qchannel_args, cchannel_args, memory_args)

        # Build the topology to ensure nl and ll are populated
        nl, ll = grid_topology.build()

        # Call methods of the grid_topology instance
        grid_topology.draw_graph()
        grid_topology.print_memory_counts()
        grid_topology.draw_memory_histogram()

        # Now you can access nl and ll
        print("Node List:", nl)
        print("Link List:", ll)

        # Generate requests
        requests_generator = Requests(grid_topology)
        scheduling = Scheduling(grid_topology)

        # Define the number of requests per round and the number of rounds
        num_requests = 30
        num_rounds = 1

        # Generate multiple rounds of requests
        all_requests = requests_generator.generate_requests_by_rounds(num_requests, num_rounds)

        # Collect all requests
        collected_requests = []
        for round_info in all_requests:
            collected_requests.extend((round_info['round_number'], req) for req in round_info['requests'])

        # Find all shortest paths for collected requests
        all_shortest_paths = requests_generator.find_all_shortest_paths(
            [(req[1], req[2]) for _, req in collected_requests])

        # Identify high weight paths
        high_weight_paths = requests_generator.identify_high_weight_paths(
            [(req[0], req[1], req[2]) for _, req in collected_requests], all_shortest_paths)

        # Print the generated requests
        total_requests = len(collected_requests)

        if total_requests <= 50:
            for round_info in all_requests:
                round_number = round_info['round_number']
                print(f"Round {round_number}:")
                for request_number, request in enumerate(round_info['requests'], start=1):
                    request_id, src, dst = request
                    manhattan_distance = requests_generator.calculate_manhattan_distance(
                        grid_topology.nl[int(src[1:]) - 1],
                        grid_topology.nl[int(dst[1:]) - 1])
                    print(f"  {request_id}: {src} -> {dst}")
                    print(f"    Manhattan Distance: {manhattan_distance}")
                    if (src, dst) in all_shortest_paths:
                        path_list = all_shortest_paths[(src, dst)]
                        if path_list:
                            for idx, path in enumerate(path_list, start=1):
                                print(f"    Shortest Path {idx}: {' -> '.join(path)}")
                        else:
                            print("    No path found.")
                    print()

            # Display high weight paths
            requests_generator.display_high_weight_paths(high_weight_paths)
        else:
            print("Total number of requests exceeds 50. Detailed information is omitted to save space.")

        # Perform FIFO scheduling
        fifo_schedules = scheduling.fifo_schedule(all_requests)

        # Display FIFO schedule
        scheduling.display_schedule(fifo_schedules, "FIFO")

        # Calculate FIFO total delay
        fifo_total_delay = scheduling.calculate_total_delay(fifo_schedules[0])
        print(f"Total FIFO delay: {fifo_total_delay}")

        # Plot the first round FIFO schedule
        scheduling.plot_first_round_schedule(fifo_schedules[0], "FIFO Schedule", max(ts for _, ts in fifo_schedules[0]))

        # Perform FIFO merge scheduling
        fifo_merged_schedules = scheduling.fifo_merge(fifo_schedules[0], all_requests)

        # Calculate FIFO Merge total delay
        fifo_merge_total_delay = scheduling.calculate_total_delay(fifo_merged_schedules)
        print(f"Total FIFO Merge delay: {fifo_merge_total_delay}")

        # Plot the first round FIFO Merge schedule
        scheduling.plot_first_round_schedule(fifo_merged_schedules, "FIFO Merge Schedule", max(ts for _, ts in fifo_merged_schedules))

        # Perform RRRN scheduling
        k = 1  # Example value for k
        c = 1  # Example value for c
        a = 1  # Example value for a
        rrrn_schedules, pre_merge_schedules = scheduling.rrrn_schedule(all_requests, k, c, a)

        # Display RRRN schedule (before and after merge)
        print("RRRN Schedule (before merge):")
        scheduling.display_schedule(pre_merge_schedules, "RRRN Before Merge")

        # Calculate RRRN before merge total delay
        rrrn_before_merge_total_delay = scheduling.calculate_total_delay(pre_merge_schedules[0])
        print(f"Total RRRN before merge delay: {rrrn_before_merge_total_delay}")

        print("RRRN Schedule (after merge):")
        scheduling.display_schedule(rrrn_schedules, "RRRN After Merge")

        # Calculate RRRN after merge total delay
        rrrn_after_merge_total_delay = scheduling.calculate_total_delay(rrrn_schedules[0])
        print(f"Total RRRN after merge delay: {rrrn_after_merge_total_delay}")

        # Plot the first round RRRN schedule (before and after merge)
        scheduling.plot_first_round_schedule(pre_merge_schedules[0], "RRRN Schedule Before Merge", max(ts for _, ts in pre_merge_schedules[0]))
        scheduling.plot_first_round_schedule(rrrn_schedules[0], "RRRN Schedule After Merge", max(ts for _, ts in rrrn_schedules[0]))

        # Print summary
        print(f"\nTotal number of rounds: {num_rounds}")
        print(f"Total number of requests: {total_requests}")

        # Define failure probability
        failure_probability = 0.1

        # Determine the number of timeslots from FIFO schedules
        num_timeslots = max(ts for schedule in fifo_schedules for _, ts in schedule)

        # Generate failure nodes
        failure_nodes = scheduling.generate_failure_nodes(nodes_number, num_timeslots, failure_probability)
        print(f"Generated failure nodes: {failure_nodes}")

        # Check and print failed requests for each schedule based on failure nodes
        schedules = {
            "FIFO": fifo_schedules[0],
            "FIFO Merge": fifo_merged_schedules,
            "RRRN": pre_merge_schedules[0],  # Use pre_merge_schedules for RRRN
            "RRRN Merge": rrrn_schedules[0]  # Use merged schedules for RRRN Merge
        }

        failed_requests = scheduling.check_failures_across_schedules(schedules, high_weight_paths, failure_nodes)

        total_failures = {"FIFO": 0, "FIFO Merge": 0, "RRRN": 0, "RRRN Merge": 0}

        # Initial number of timeslots used by each schedule
        timeslots_used = {
            "FIFO": max(ts for _, ts in fifo_schedules[0]),
            "FIFO Merge": max(ts for _, ts in fifo_merged_schedules),
            "RRRN": max(ts for _, ts in pre_merge_schedules[0]),
            "RRRN Merge": max(ts for _, ts in rrrn_schedules[0])
        }

        for timeslot, nodes in failure_nodes.items():
            print(f"\nTimeslot {timeslot} failed nodes: {nodes}")
            for schedule_name, schedule in schedules.items():
                requests_in_timeslot = [request_id for request_id, ts in schedule if ts == timeslot]
                print(f"  {schedule_name} requests in Timeslot {timeslot}: {requests_in_timeslot}")
                if schedule_name in failed_requests:
                    if timeslot in failed_requests[schedule_name]:
                        failed = [req for req in failed_requests[schedule_name][timeslot] if "无requests" not in req]
                        print(f"  Failed requests in {schedule_name} Timeslot {timeslot}: {failed}")
                        total_failures[schedule_name] += len(failed)

        print(f"\nTotal failed requests:")
        for schedule_name, failures in total_failures.items():
            print(f"  {schedule_name}: {failures}")

        # Calculate and print the total timeslots including failed requests
        total_timeslots_with_failures = {
            schedule_name: timeslots_used[schedule_name] + failures
            for schedule_name, failures in total_failures.items()
        }

        print("\nTotal timeslots including failed requests:")
        for schedule_name, total_ts in total_timeslots_with_failures.items():
            print(f"  {schedule_name}: {total_ts}")

if __name__ == "__main__":
    main()

    # Reset stdout to default
    sys.stdout = sys.__stdout__
    print("Output has been written to output.txt")
