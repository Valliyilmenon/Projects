#!/usr/bin/python3 
"""
Name 	Email 	Github Username
Valliyil SaiKiran 	valliyilmenon@gmail.com 	Valliyilmenon
Singh Swati 	er.swatisingh86@gmail.com 	SwatiSingh86
Tinubu, Oluwaseyi 	tinubuseyi@gmail.com 	Decastrino
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__))+'/components')
import random
import time

from sim_components import *

"""
This is a starter pack for a cpu scheduling project. The code / classes provided are to give you a
head start in creating the scheduling simulation. Obviously this is a simulation, so the majority
of the concepts are "simulated". For example, process "burst times" and "IO times" are known
a-priori (not so in real world). Things like memory are abstracted from addressable locations and
page tables to total "blocks" needed.
"""


###################################################################################################

# === Class: MLFQ===

class MLFQ(object):
    """Multi-Level Feedback Queue

    - Some general requirements for a MLFQ:
        - Each queue needs its own scheduling algorithm (typically Fcfs).
        - The method used to determine when to upgrade a process to a higher-priority queue.
        - The method used to determine when to demote a process to a lower-priority queue.
        - The method used to determine which queue a process will enter when that process needs
        service.

    - Rule 1: If Priority(A) > Priority(B), A runs (B doesn't).
    - Rule 2: If Priority(A) = Priority(B), A & B run in RR.
    - Rule 3: When a job enters the system, it is placed at the highest priority (the topmost
              queue).
    - Rule 4: Once a job uses up its time allotment at a given level (regardless of how many times
              it has given up the CPU), its priority is reduced (i.e., it moves down one queue).
    - Rule 5: After some time period S, move all the jobs in the system to the topmost queue.

    - **Attributes**:
        - self.num_levels
        - self.queues
    """
    def __init__(self, num_levels=2):
        self.num_levels = num_levels
        self.queues = []

        for i in range(self.num_levels):
            self.queues.append(Fifo())

    def new(self, process):
        """This method admits a new process into the system.

        - **Args:**
            - None
        - **Returns:**
            - None
        """
        self.queues[0].add(process)

    def __str__(self):
        """Visual dump of class state.

        - **Args:**
            - None
        - **Returns:**
            - None
        """
        return MyStr(self)

###################################################################################################

# === Class: Scheduler===

class Scheduler(object):
    """
    New:        In this status, the Process is just made or created.
    Running:    In the Running status, the Process is being executed.
    Waiting:    The process waits for an event to happen for example an input from the keyboard.
    Ready:      In this status the Process is waiting for execution in the CPU.
    Terminated: In this status the Process has finished its job and is ended.
    """



    def __init__(self, *args, **kwargs):
        self.clock = Clock()
        self.memory = Memory()                  
        self.cpu = Cpu()
        # self.accounting = SystemAccounting()
        self.semaphore_pool = MySemaphorePool()
        self.job_scheduling_queue = Fifo()
        self.ready_queue = MLFQ()
        self.system_status_list = SystemStatusList()
        self.event_type = None


# Printing flags
        self.new_event = None
        self.t_event = None
        self.e_event = None
        self.memory_full = None
        self.i_event = None
        self.c_event = None
        self.sem_acquired_flag = None  # A flag to indicate whether a semaphore was successfully acquired
        self.sem_flag = None
        self.io_dict = {}  # A list to keep the IO Wait Queue



    def new_process(self, job_info):
        """New process entering system gets placed on the 'job_scheduling_queue'.
        - **Args**:
            - job_info (dict): Contains new job information.
        - **Returns**:
            - None
        """
        if int(job_info['mem_required']) > self.memory.mem_size:
            self.memory_full = True
        else:
            self.job_scheduling_queue.add(Process(**job_info))
            self.system_status_list.job_scheduling_queue_list.add(Process(**job_info))

    def fill_ready_queue(self):
        """ Check whether first job on job_scheduling_queue can be inserted to ready_queue
        and insert if possible.
        - **Args**:
            - None
        - **Returns**:
            -None
        """

        # Memory allocation
        if not self.job_scheduling_queue.empty():
            if self.memory.allocate(self.job_scheduling_queue.first())['success']:  # If there is enough memory

                self.job_scheduling_queue.first().rem_from_sq = self.clock.current_time()

                self.ready_queue.queues[0].add(self.job_scheduling_queue.first())  # Add job to ready_queue level1

                self.system_status_list.ready_queue_list_lvl1.add(self.system_status_list.job_scheduling_queue_list.first())

                # self.system_status_list.ready_queue_list_lvl1.first().rem_from_sq = self.clock.current_time()

                self.job_scheduling_queue.remove()  # Remove job from scheduling_queue

                self.system_status_list.job_scheduling_queue_list.remove()  # Remove job from scheduling_queue status list



    def perform_io(self, info):
        """Current process on cpu performs io
        """
        if self.cpu.busy():
            self.i_event = True
            removed_process = self.cpu.remove_process()
            removed_process['pid'].complete_cpu_cycles += removed_process['run_time']
            temp_info = {'job': removed_process['pid'],
                         'io_start': info['time'],
                         'io_burst': info['ioBurstTime'],
                         'io_comp_time': int(info['time']) + int(info['ioBurstTime']),
                         'io_comp_cycles': 0}
            # self.io_list.insert(int(removed_process['pid'].process_id), temp_info)
            self.io_dict[removed_process['pid'].process_id] = temp_info
        else:
            return None



    def sem_acquire(self, info):
        """Acquire one of the semaphores
        """
        # If no available semaphore, job goes to waiting queue
        self.sem_acquired_flag = None
        if self.cpu.busy():
            if self.semaphore_pool.acquire(sem_num=info['semaphore'], job=self.cpu.running_process) is None:
                self.sem_acquired_flag = 0
            else:
                self.sem_acquired_flag = True
        else:
            print('DEBUG: Tried to acquire semaphore while CPU is idle')




    def sem_release(self, info):
        """Release one of the semaphores
        """
        self.sem_flag = None
        # if self.cpu.busy():
        job_to_move = self.semaphore_pool.release(process_id=self.cpu.running_process.process_id, sem_num=info['semaphore'])
        if job_to_move is not None:  # A job from the semaphore waiting queue has acquired the semaphore
            # self.sem_flag = True

            self.ready_queue.queues[0].add(job_to_move)  # Move to ready_queue level2
            self.system_status_list.ready_queue_list_lvl1.add(job_to_move)

###################################################################################################






# === Class: Simulator===

class Simulator(object):
    """
    Not quite sure yet
    """
    def __init__(self, **kwargs):

        # Must have input file to continue
        if 'input_file' in kwargs:
            self.input_file = kwargs['input_file']
        else:
            raise Exception("Input file needed for simulator")
        
        # Can pass a start time in to init the system clock.
        if 'start_clock' in kwargs:
            # self.input_file = kwargs['start_clock']
            self.start_clock = kwargs['start_clock']
        else:
            self.start_clock = 0

        self.ticks_cntr = 0
        self.current_process_running_time = 0
        self.max_cpu_ticks_lvl1 = 100
        self.max_cpu_ticks_lvl2 = 300
        self.cpu_ticks = self.max_cpu_ticks_lvl1
        self.print_event = None
        self.memory_status = None
        self.running_job = None

        # Read jobs in apriori from input file.
        self.jobs_dict = load_process_file(self.input_file,return_type="Dict")

        # create system clock and do a hard reset it to make sure
        # its a fresh instance. 
        self.system_clock = Clock()
        self.system_clock.hard_reset(self.start_clock)

        # Initialize all the components of the system. 
        self.scheduler = Scheduler()    
        self.memory = Memory()
        self.cpu = Cpu()
        # self.accounting = SystemAccounting()
        self.system_status_list = SystemStatusList()

        # This dictionary holds key->value pairs where the key is the "event" from the input
        # file, and the value = the "function" to be called.
        # A = new process enters system             -> calls scheduler.new_process
        # D = Display status of simulator           -> calls display_status
        # I = Process currently on cpu performs I/O -> calls scheduler.perform_io 
        # S = Semaphore signal (release)            -> calls scheduler.sem_acquire
        # W = Semaphore wait (acquire)              -> calls scheduler.sem_release
        self.event_dispatcher = {
            'A': self.scheduler.new_process,
            'D': self.display_status,
            'I': self.scheduler.perform_io,
            'W': self.scheduler.sem_acquire,
            'S': self.scheduler.sem_release
        }


        # Start processing jobs:
        
        # While there are still jobs to be processed
        while len(self.jobs_dict) > 0:
            # Events are stored in dictionary with time as the key
            key = str(self.system_clock.current_time())

            # if key == '12492':  # For debug only
            #     print('DEBUG')

            # If current time is a key in dictionary, run that event.
            if key in self.jobs_dict.keys():
                event_data = self.jobs_dict[key]
                self.event_type = event_data['event']
                if 'complete_cpu_cycles' not in event_data:
                    event_data['complete_cpu_cycles'] = 0
                self.scheduler.new_event = True
                # Call appropriate function based on event type
                self.event_dispatcher[self.event_type](event_data)
                # Remove job from dictionary
                del self.jobs_dict[key]

            # Check if a job failed to acquire a semaphore and moved to semaphore waiting queue. If so - remove it from
            # the CPU
            self.manage_semaphores()
            # Check whether the currently running job should be removed from the CPU due to termination or time
            # quantum expiry
            self.check_cpu_status()
            # Check whether any jobs in the IO queue have completed IO operation and should be moved back to ready_queue
            self.check_io_queue()
            # Move jobs from job_scheduling_queue to ready_queue (while checking memory requirements)
            self.scheduler.fill_ready_queue()
            # If CPU is idle check whether there are any jobs in ready_queue (including level1/2 prioritization) and
            # run the appropriate job. If CPU is busy check whether currently running job is from ready_queue level2
            # and there is a job waiting in ready_queue level 1, and if so suspend the running job and run the job from
            # ready_queue level1
            self.deploy_cpu()
            # Print output to stdout
            self.print_output()
            # Increment system clock
            self.system_clock += 1

        # Keep system running in case there aren't any new jobs left to be processed,
        # but some jobs are still in the pipe
        while self.cpu.running_process is not None:
            self.check_cpu_status()
            # self.scheduler.fill_ready_queue()
            self.deploy_cpu()
            self.print_output()
            self.system_clock += 1

        self.final_display()  # Print final data to stdout

        # Clear the finished list - only required if running more than 1 input file
        self.system_status_list.finished_list.list = []



    def manage_semaphores(self):
        if self.scheduler.sem_acquired_flag == 0:  # Check if current job was added to semaphore waiting queue
            # Remove current job from CPU
            removed_process = self.cpu.remove_process()
            self.running_job = None
            self.ticks_cntr = 0
            removed_process['pid'].complete_cpu_cycles += removed_process['run_time']
            self.scheduler.sem_acquired_flag = None

        # if self.scheduler.sem_flag:
        #     removed_process = self.cpu.remove_process()
        #     self.running_job = None
        #     self.ticks_cntr = 0
        #     removed_process['pid'].complete_cpu_cycles += removed_process['run_time']
        #     self.scheduler.sem_flag = None
        #     if removed_process['pid'].state == 'lvl1':  # Move job to ready_queue level1
        #         self.scheduler.ready_queue.queues[0].add(removed_process['pid'])  # Move to ready_queue level2
        #         self.scheduler.system_status_list.ready_queue_list_lvl1.add(removed_process['pid'])
        #     elif removed_process['pid'].state == 'lvl2':  # Move job to ready_queue level2
        #         self.scheduler.ready_queue.queues[1].add(removed_process['pid'])  # Move to ready_queue level2
        #         self.scheduler.system_status_list.ready_queue_list_lvl2.add(removed_process['pid'])
        #     else:
        #         print('DEBUG: Wrong state')
        #
        #     self.cpu.run_process(self.scheduler.job_to_move)  # Run job
        #     self.running_job = self.scheduler.job_to_move
        #     self.ticks_cntr = 1

    def check_cpu_status(self):
        """ Check whether the currently running job should be removed from the CPU due to termination or time
            quantum expiry
        
        :return: None 
        """
        if self.cpu.busy():
            # Determine whether use time_quantum for level 1 (100) or level 2 (300)
            if self.cpu.running_process.state is 'lvl2':
                self.cpu_ticks = self.max_cpu_ticks_lvl2
            elif self.cpu.running_process.state is 'lvl1':
                self.cpu_ticks = self.max_cpu_ticks_lvl1
            else:
                print('Unknown state')

            if self.ticks_cntr >= (int(self.cpu.running_process.burst_time) - int(
                    self.cpu.running_process.complete_cpu_cycles)):  # If job has completed its required cpu cycles
                # Remove job from CPU
                removed_process = self.cpu.remove_process()
                # self.running_job = None
                # Update amount of complete CPU cycles
                removed_process['pid'].complete_cpu_cycles += removed_process['run_time']
                # Put the job on the finished_list
                self.system_status_list.finished_list.add(self.running_job, start_time=self.running_job.start_time, com_time=self.system_clock.clock)
                # Deallocate memory
                self.memory.deallocate(removed_process['pid'].process_id)
                # self.scheduler.semaphore_pool.release(removed_process['pid'].process_id)
                self.ticks_cntr = 0
                # Set termination event flag for printing
                self.scheduler.t_event = True

            elif self.ticks_cntr >= self.cpu_ticks:  # If job has ran more than allowed quantum
                # Remove job from CPU
                removed_process = self.cpu.remove_process()
                self.running_job = None
                self.ticks_cntr = 0
                removed_process['pid'].complete_cpu_cycles += removed_process['run_time']
                # Add removed job to ready_queue level 2
                self.scheduler.ready_queue.queues[1].add(removed_process['pid'])
                # Update system_status_list
                self.system_status_list.ready_queue_list_lvl2.add(removed_process['pid'])
                # Set E event flag for printing
                self.scheduler.e_event = True

            else:
                self.ticks_cntr += 1

    def deploy_cpu(self):
        """ If CPU is idle check whether there are any jobs in ready_queue (including level1/2 prioritization) and
            run the appropriate job. If CPU is busy check whether currently running job is from ready_queue level2
            and there is a job waiting in ready_queue level 1, and if so suspend the running job and run the job from
            ready_queue level1
        
        :return: None
        """
        if not self.cpu.busy():
            self.ticks_cntr = 0
            if not self.scheduler.ready_queue.queues[0].empty():  # Take jobs from ready_queue level1
                self.scheduler.ready_queue.queues[0].first().state = 'lvl1'
                self.cpu.run_process(self.scheduler.ready_queue.queues[0].first())  # Run job
                self.running_job = self.scheduler.ready_queue.queues[0].first()
                # if self.running_job.complete_cpu_cycles == 0:
                if self.running_job.start_time is None:
                    self.running_job.start_time = self.system_clock.clock
                self.scheduler.ready_queue.queues[0].remove()  # Remove the process from ready_queue
                self.system_status_list.ready_queue_list_lvl1.remove()
                self.ticks_cntr += 1
            else:  # ready_queue level1 is empty - try level2
                if not self.scheduler.ready_queue.queues[1].empty():  # Take jobs from ready_queue level2
                    self.scheduler.ready_queue.queues[1].first().state = 'lvl2'
                    self.cpu.run_process(self.scheduler.ready_queue.queues[1].first())  # Run job
                    self.running_job = self.scheduler.ready_queue.queues[1].first()
                    # self.running_job.start_time = self.system_clock.clock
                    self.scheduler.ready_queue.queues[1].remove()   # Remove the process from ready_queue
                    self.system_status_list.ready_queue_list_lvl2.remove()
                    self.ticks_cntr += 1
        else:  # CPU is busy - check if there are jobs in level1 and priorotize them over level2
            # Running job is from ready_queue level 2 and level1 queue is not empty
            if self.cpu.running_process.state is 'lvl2' and not self.scheduler.ready_queue.queues[0].empty():
                removed_process = self.cpu.remove_process()  # Remove job from CPU
                removed_process['pid'].complete_cpu_cycles += removed_process['run_time']  # Update amount of clocks job ran
                self.ticks_cntr = 0
                self.scheduler.ready_queue.queues[1].add(removed_process['pid'])  # Move to ready_queue level2
                self.system_status_list.ready_queue_list_lvl2.add(removed_process['pid'])
                self.scheduler.ready_queue.queues[0].first().state = 'lvl1'
                self.cpu.run_process(self.scheduler.ready_queue.queues[0].first())  # Run job from ready_queue level1
                self.running_job = self.scheduler.ready_queue.queues[0].first()
                self.system_status_list.ready_queue_list_lvl1.remove()
                self.scheduler.ready_queue.queues[0].remove()  # Remove the job from ready_queue
                self.ticks_cntr += 1

    def check_io_queue(self):
        """ Check whether any jobs in the IO queue have completed IO operation and should be moved back to ready_queue
        
        :return: None
        """
        jobs_2_remove = []
        for job in self.scheduler.io_dict:

            if self.scheduler.io_dict[job]['io_comp_cycles'] >= int(self.scheduler.io_dict[job]['io_burst']):
                # self.scheduler.io_dict[job]['job'].state = 'lvl1' # job is moving to ready_queue lvl1 even if it came from lvl2
                self.scheduler.ready_queue.queues[0].add(self.scheduler.io_dict[job]['job'])  # Add job to ready_queue level1
                self.system_status_list.ready_queue_list_lvl1.add(self.scheduler.io_dict[job]['job'])
                self.scheduler.c_event = True
                jobs_2_remove.append(job)
            else:
                self.scheduler.io_dict[job]['io_comp_cycles'] += 1

        for value in jobs_2_remove:
            del self.scheduler.io_dict[value]  # Remove job from io queue

    def final_display(self):
        """ Print final information to stdout (including calculation of Average Turnaround Time and 
        Average Job Scheduling Wait Time
        
        :return: 
        """
        av_ta = 0  # Average turnaround time
        av_wait = 0  # Average job scheduling wait time
        num_jobs = 0

        print('The contents of the FINAL FINISHED LIST')
        print('---------------------------------------')
        print('Job #  Arr. Time  Mem. Req.  Run Time  Start Time  Com. Time')
        print('-----  ---------  ---------  --------  ----------  ---------')
        for job in self.system_status_list.finished_list.list:
            print('{:<11}{:<11}{:<11}{:<11}{:<11}{:<11}'.format(job.process_id, job.time, job.mem_required,
                                                                job.burst_time, job.start_time, job.com_time))

            av_ta += int(job.com_time) - int(job.time)
            # av_wait += int(job.rem_from_sq) - int(job.time)
            av_wait += int(job.rem_from_sq) - int(job.time)
            num_jobs += 1

        # # Some tricks to trim the average result without rounding it
        # my_temp = av_ta/num_jobs
        # av_ta = str(round(av_ta / num_jobs, 4))
        # av_wait = str(round(av_wait/num_jobs, 4))

        # print('The Average Turnaround Time for the simulation was {} units.'.format(av_ta[:len(av_ta) - 1]))
        # print('The Average Job Scheduling Wait Time for the simulation was {} units.'.format(av_wait[:len(av_wait) - 1]))


        # PLEASE NOTE: The average time result is slightly different from the one in the expected output file
        # since the round() function in python 3 is different from python 2 (which was probably used for the original
        # output). Use the above method to trim digits instead of rounding the result

        print('The Average Turnaround Time for the simulation was {} units.'.format(round(av_ta/num_jobs, 3)))
        print('The Average Job Scheduling Wait Time for the simulation was {} units.'.format(round(av_wait/num_jobs, 3)))
        print('There are {} blocks of main memory available in the system.'.format(self.memory.blks_avail))

    def print_output(self):
        """ Print events (both internal and external) to stdout
        
        :return: None
        """
        if self.scheduler.t_event:
            print('Event: T   Time: {}'.format(self.system_clock.clock))
            self.scheduler.t_event = None

        if self.scheduler.c_event:
            print('Event: C   Time: {}'.format(self.system_clock.clock))
            self.scheduler.c_event = None

        if self.scheduler.new_event:
            print('Event: {}   Time: {}'.format(self.event_type, self.system_clock.clock))
            self.scheduler.new_event = None
            if self.event_type is 'D':
                self.print_status()

        if self.scheduler.e_event:
            print('Event: E   Time: {}'.format(self.system_clock.clock))
            self.scheduler.e_event = None

        if self.scheduler.memory_full:
            print('This job exceeds the system\'s main memory capacity.')
            self.scheduler.memory_full = None

        # if self.scheduler.i_event:
        #     print('Event: I   Time: {}'.format(self.system_clock.clock))
        #     self.scheduler.i_event = None

    def print_status(self):
        """ Print "Status Display" following the D event
        
        :return: None
        """
        print('************************************************************')
        print('The status of the simulator at time {}.'.format(self.system_clock.clock))
        print('The contents of the JOB SCHEDULING QUEUE')
        print('----------------------------------------')

        if self.system_status_list.job_scheduling_queue_list.empty():
            print('The Job Scheduling Queue is empty.')
        else:
            print('Job #  Arr. Time  Mem. Req.  Run Time')
            print('-----  ---------  ---------  --------')

            for job in self.system_status_list.job_scheduling_queue_list.list:
                print('{:<11}{:<11}{:<11}{:<11}'.format(job.process_id,
                                                                    job.time,
                                                                    job.mem_required,
                                                                    job.burst_time))

        print('The contents of the FIRST LEVEL READY QUEUE')
        print('-------------------------------------------')
        if self.system_status_list.ready_queue_list_lvl1.empty():
            print('The First Level Ready Queue is empty.')
        else:
            print('Job #  Arr. Time  Mem. Req.  Run Time')
            print('-----  ---------  ---------  --------')
            for job in self.system_status_list.ready_queue_list_lvl1.list:
                print('{:<11}{:<11}{:<11}{:<11}'.format(job.process_id,
                                                                    job.time,
                                                                    job.mem_required,
                                                                    job.burst_time))

        print('The contents of the SECOND LEVEL READY QUEUE')
        print('--------------------------------------------')
        if self.system_status_list.ready_queue_list_lvl2.empty():
            print('The Second Level Ready Queue is empty.')
        else:
            print('Job #  Arr. Time  Mem. Req.  Run Time')
            print('-----  ---------  ---------  --------')
            for job in self.system_status_list.ready_queue_list_lvl2.list:
                print('{:<11}{:<11}{:<11}{:<11}'.format(job.process_id,
                                                                    job.time,
                                                                    job.mem_required,
                                                                    job.burst_time))

        print('The contents of the I/O WAIT QUEUE')
        print('----------------------------------')

        if len(self.scheduler.io_dict) == 0:
            print('The I/O Wait Queue is empty.')
        else:
            print('Job #  Arr. Time  Mem. Req.  Run Time  IO Start Time  IO Burst  Comp. Time')
            print('-----  ---------  ---------  --------  -------------  --------  ----------')
            for process in self.scheduler.io_dict:
                print('{:<11}{:<11}{:<11}{:<11}{:<11}{:<11}{:<11}'.format(process,
                      self.scheduler.io_dict[process]['job'].time,
                      self.scheduler.io_dict[process]['job'].mem_required,
                      self.scheduler.io_dict[process]['job'].burst_time,
                      self.scheduler.io_dict[process]['io_start'],
                      self.scheduler.io_dict[process]['io_burst'],
                      self.scheduler.io_dict[process]['io_comp_time']))


        self.display_semaphore_status()

        print('The CPU  Start Time  CPU burst time left')
        print('-------  ----------  -------------------')
        if self.cpu.busy():
            time_left = int(self.cpu.running_process.burst_time) - int(self.cpu.running_process.complete_cpu_cycles) - int(self.ticks_cntr) + 1
            print('{:<11}{:<11}{:<11}'.format(self.cpu.running_process.process_id,
                                                                    self.running_job.start_time,
                                                                    time_left))
        else:
            print('The CPU is idle.')

        print('The contents of the FINISHED LIST')
        print('---------------------------------')
        print('Job #  Arr. Time  Mem. Req.  Run Time  Start Time  Com. Time')
        print('-----  ---------  ---------  --------  ----------  ---------')
        for job in self.system_status_list.finished_list.list:
            print('{:<11}{:<11}{:<11}{:<11}{:<11}{:<11}'.format(job.process_id, job.time, job.mem_required, job.burst_time, job.start_time, job.com_time))

        print('There are {} blocks of main memory available in the system.'.format(self.memory.blks_avail))

    def display_status(self, info):
        """ Legacy
        
        :param info: 
        :return: None
        """
        pass

    def display_semaphore_status(self):
        """ Print semaphores values and waiting queues to stdout
        
        :return: None
        """
        print('The contents of SEMAPHORE ZERO')
        print('------------------------------')
        print('The value of semaphore 0 is {}.'.format(self.scheduler.semaphore_pool.sem_dict[0].value))
        if self.scheduler.semaphore_pool.sem_dict[0].waiting_queue.empty():
            print('The wait queue for semaphore 0 is empty.')
        else:
            self.print_fifo_pid(self.scheduler.semaphore_pool.sem_dict[0].waiting_queue)

        print('The contents of SEMAPHORE ONE')
        print('-----------------------------')
        print('The value of semaphore 1 is {}.'.format(self.scheduler.semaphore_pool.sem_dict[1].value))
        if self.scheduler.semaphore_pool.sem_dict[1].waiting_queue.empty():
            print('The wait queue for semaphore 1 is empty.')
        else:
            self.print_fifo_pid(self.scheduler.semaphore_pool.sem_dict[1].waiting_queue)

        print('The contents of SEMAPHORE TWO')
        print('-----------------------------')
        print('The value of semaphore 2 is {}.'.format(self.scheduler.semaphore_pool.sem_dict[2].value))
        if self.scheduler.semaphore_pool.sem_dict[2].waiting_queue.empty():
            print('The wait queue for semaphore 2 is empty.')
        else:
            self.print_fifo_pid(self.scheduler.semaphore_pool.sem_dict[2].waiting_queue)


        print('The contents of SEMAPHORE THREE')
        print('-------------------------------')
        print('The value of semaphore 3 is {}.'.format(self.scheduler.semaphore_pool.sem_dict[3].value))
        if self.scheduler.semaphore_pool.sem_dict[3].waiting_queue.empty():
            print('The wait queue for semaphore 3 is empty.')
        else:
            self.print_fifo_pid(self.scheduler.semaphore_pool.sem_dict[3].waiting_queue)


        print('The contents of SEMAPHORE FOUR')
        print('------------------------------')
        print('The value of semaphore 4 is {}.'.format(self.scheduler.semaphore_pool.sem_dict[4].value))
        if self.scheduler.semaphore_pool.sem_dict[4].waiting_queue.empty():
            print('The wait queue for semaphore 4 is empty.')
        else:
            self.print_fifo_pid(self.scheduler.semaphore_pool.sem_dict[4].waiting_queue)

    def print_fifo_pid(self, fifo):
        """ Iterate over all fifo values and print them to stdout (based on the Fifo class)
        
        :param fifo: Fifo object 
        :return: None
        """
        for i in range(len(fifo.Q)):
            print(fifo.ret_indx_val(i).process_id)

    def __str__(self):
        """
        Visual dump of class state.
        """
        return my_str(self)


###################################################################################################
# Test Functions
###################################################################################################

def run_tests():
    print("############################################################")
    print("Running ALL tests .....\n")

    test_process_class()
    test_class_clock()
    test_cpu_class()
    test_memory_class()
    test_semaphore_class()


if __name__ == '__main__':

    file_name1 = os.path.dirname(os.path.realpath(__file__)) + '/input_data/jobs_in_a.txt'
    file_name2 = os.path.dirname(os.path.realpath(__file__)) + '/input_data/jobs_in_b.txt'
    file_name3 = os.path.dirname(os.path.realpath(__file__)) + '/input_data/jobs_in_c.txt'


    test_files = [file_name1, file_name2, file_name3]
    for file in test_files:
        S = Simulator(input_file=file)
