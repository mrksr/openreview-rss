from .sessions import Sessions, Session
import numpy as np
import random
from tqdm import tqdm
import pickle
import multiprocessing as mp

class EnergyMatcher:
    """
    This class implements the energy-based sequential assignment algorithm for match papers and ACs to sessions.
    """

    class Score:
        """
        Class to store the score of a solution.
        """
        def __init__(self, num_papers =0, num_secondary_acs=0, energy=-np.inf):
            self.num_papers = num_papers
            self.num_secondary_acs = num_secondary_acs
            self.energy = energy

    def __init__(self, energy_fn=None,
                    second_ac_greedy=True,
                    assign_secondary_acs=True,
                    prefer_assigned_sac=False,
                    secondary_ac_max_load=3,
                    num_iterations=1000,
                    num_threads=mp.cpu_count(),
                    checkpoint_num_it=None,
                    checkpoint_file=None):
        # The energy to maximize. Takes in all sessions and secondary AC assignments and returns a score. Default is the mean affinity of all papers and ACs in the session + mean affinity of all secondary ACs.
        self.energy_fn = energy_fn if energy_fn is not None else self.default_energy
        
        # Assignment settings.
        self.second_ac_greedy = second_ac_greedy # If true assign the acs greedily instead of random.
        self.assign_secondary_acs = assign_secondary_acs # If true assign secondary acs to the papers. If false, only assign the papers to sessions and fill the sessions with the acs.
        self.secondary_ac_max_load = secondary_ac_max_load  # Maximum number of assignments per secondary AC.
        self.prefer_assigned_sac = prefer_assigned_sac # If true, assign papers to their SACs if possible.

        # Optimization parameters.
        self.num_iterations = num_iterations
        self.num_threads = num_threads # Number of threads to use for optimization.
        self.checkpoint_num_it = checkpoint_num_it # Save a checkpoint every n iterations.
        self.checkpoint_file = checkpoint_file # Path to save the checkpoint to.

        # Solution tracking.
        self._best_solution = None
        self._best_score = self.Score()
        self.stats ={} # {it: score} each time the score improves.

        # Problem data. These are all read only.
        self.papers = None # List of paper numbers to assign to sessions.
        self.affinities = None  # Dict of {paper_no: {(S)AC: score}}. For all affinities that exist. includes ACs and SACs.
        self.conflicts = None   # Dict of {paper_no: set((S)ACs)}. For all conflicts that exist. Includes ACs and SACs.
        self.ac_assignments = None # Dict of {paper_no: set(ACs)}. For each paper all assigned ACs, excluding SACs.
        self.sac_assignments = None # Dict of {paper_no: set(SACs)}. For each paper all assigned SACs.
        self.sessions = None # Sessions object containing the layout of all sessions to match papers and ACs to, excluding the Standout.
        self.all_acs = None # Set of all available ACs.

    def default_energy(self, sessions: Sessions, secondary_ac_assignments: dict):
        """
        Default energy function to maximize.
        :param sessions: Sessions object containing session data.
        :param secondary_ac_assignments: Secondary AC assignments for each paper. {paper_no: ac}
        :return: Energy score.
        """
        # Default energy is the mean affinity of all papers and (S)ACs in the session + mean affinity of all secondary ACs.
        session_affinities = []
        for session in sessions.sessions:
            affs = [self.affinities[p].get(ac, 0) for p in session.papers for ac in session.acs]
            affs.extend([self.affinities[p].get(sac, 0) for p in session.papers for sac in session.sacs])
            if affs:
                session_affinities.append(np.mean(affs))
        
        ac_affinities = [self.affinities[paper].get(ac,0) for paper, ac in secondary_ac_assignments.items()]
        return np.mean(session_affinities if session_affinities else 0) + np.mean(ac_affinities if ac_affinities else 0)

    def setup_problem(self, sessions: Sessions, papers, conflicts, affinities, ac_assignments, sac_assignments, all_acs):
        """
        Set the problem for the matcher.
        :param sessions: Sessions object containing session data.
        :param papers: List of paper numbers to assign to sessions.
        :param conflicts: Conflicts for each paper. {paper_no: set(ACs)}
        :param affinities: Affinity scores for each paper. {paper_no: {AC: score}}
        :param ac_assignments: AC assignments for each paper. {paper_no: set(ACs)}
        :param sac_assignments: SAC assignments for each paper. {paper_no: set(SACs)}
        :param all_acs: Set of all ACs.
        """
        self.sessions = sessions
        self.papers = papers
        self.conflicts = conflicts
        self.affinities = affinities
        self.ac_assignments = ac_assignments
        self.sac_assignments = sac_assignments
        self.all_acs = all_acs
        self._verify_problem()
    

    def _verify_config(self):
        """
        Verify the matcher configuration.
        :raises ValueError: If the configuration is invalid.
        """
        if not isinstance(self.prefer_assigned_sac, bool):
            raise ValueError(f"Invalid prefer_assigned_sac: {self.prefer_assigned_sac}. Must be a boolean.")
        if not isinstance(self.num_iterations, int) or self.num_iterations <= 0:
            raise ValueError(f"Invalid num_iterations: {self.num_iterations}. Must be a positive integer.")
        if not isinstance(self.secondary_ac_max_load, int) or self.secondary_ac_max_load <= 0:
            raise ValueError(f"Invalid secondary_ac_max_load: {self.secondary_ac_max_load}. Must be a positive integer.")
        if not isinstance(self.num_threads, int) or self.num_threads <= 0:
            raise ValueError(f"Invalid num_threads: {self.num_threads}. Must be a positive integer.")

        
    def _verify_problem(self):
        """
        Verify the matcher problem setup.
        :raises ValueError: If the setup is invalid.
        """
        if self.sessions is None:
            raise ValueError("Sessions not set. Please set the sessions before verifying.")
        if self.papers is None:
            raise ValueError("Papers not set. Please set the papers before verifying.")
        if self.affinities is None:
            raise ValueError("Affinities not set. Please set the affinities before verifying.")
        if self.conflicts is None:
            raise ValueError("Conflicts not set. Please set the conflicts before verifying.")
        if self.ac_assignments is None:
            raise ValueError("AC assignments not set. Please set the AC assignments before verifying.")
        if self.sac_assignments is None:
            raise ValueError("SAC assignments not set. Please set the SAC assignments before verifying.")
        if self.all_acs is None:
            raise ValueError("All ACs not set. Please set the all_acs before verifying.")
        if not isinstance(self.sessions, Sessions):
            raise ValueError("Sessions must be an instance of the Sessions class.")
        if not isinstance(self.papers, list):
            raise ValueError("Papers must be a list.")
        if not isinstance(self.affinities, dict):
            raise ValueError("Affinities must be a dictionary.")
        if not isinstance(self.conflicts, dict):
            raise ValueError("Conflicts must be a dictionary.")
        if not isinstance(self.ac_assignments, dict):
            raise ValueError("AC assignments must be a dictionary.")
        if not isinstance(self.sac_assignments, dict):
            raise ValueError("SAC assignments must be a dictionary.")
        if not isinstance(self.all_acs, set):
            raise ValueError("All ACs must be a set.")
    

    def _select_from_options(self, options):
        """
        Select a set of options to process.
        :param papers: dict of {key: options}, where keys are typically paper numbers, ACs or sessions.
        :return: Selected key.
        """
        # Select a paper with the fewest options.
        min_num_options = min([len(opt) for opt in options.values()])
        return random.choice([p for p, opt in options.items() if len(opt) == min_num_options])
    

    def _assign_paper(self, paper_no, paper_options, sessions):
        """
        Assign a given paper to a session.
        """
        if self.prefer_assigned_sac and paper_no in self.sac_assignments:
            # Prefer an assigned SAC if available.
            sac_indices = set()
            for sac in self.sac_assignments[paper_no]:
                sac_indices.update(sessions.indices_for_sac(sac))
            new_options = paper_options & sac_indices
            if new_options:
                random.choice(list(new_options))

        return random.choice(list(paper_options))

       
    def _prune_sac_coi(self, options):
        # Remove all SAC CoI from the options.
        for sac in self.sessions.sacs:
            invalid_sessions = set(self.sessions.indices_for_sac(sac))
            for p in options:
                if sac in self.conflicts[p]:
                    options[p] = options[p] - invalid_sessions
    

    def _prune_paper_options(self, sessions : Sessions, options, paper_no, sess_id):
        _, sess_no = sessions.keys_from_idx(sess_id)
        session = sessions.get(sess_id)
        acs = self.ac_assignments[paper_no]

        # Time constraints: Papers handled by the same ACs can not be in the same time slot.
        handled_papers = set([p for p, p_acs in self.ac_assignments.items() if (p_acs & acs)])
        invalid_indices = set(sessions.indices_for_session(sess_no))
        invalid_indices.discard(sess_id) # Can alway assign to the same session.
        for p in handled_papers:
            if p in options:
                options[p] = options[p] - invalid_indices   

         # Max num papers: Remove the session if it is full.
        if len(session.papers) >= session.max_num_papers:
            for p in options:
                options[p].discard(sess_id)
            return

        # CoI
        for p in options:
            # CoI 1: Prevent all papers that have a CoI with the newly assigned acs from the session.
            if acs & self.conflicts[p]:
                options[p].discard(sess_id) 
            # CoI 2: Prevent all papers whose ACs has a CoI with the newly assigned paper from the session.
            p_acs = self.ac_assignments[p]
            if p_acs & self.conflicts[paper_no]:
                options[p].discard(sess_id)


    def _match_papers(self):
        """
        Match all papers to sessions.
        """
        # Create the working copy of the sessions for this iteration.
        sessions = self.sessions.copy()

        # For each paper, create the options grid. Initially, all papers are available for all sessions.
        options = {p : set([i for i, _ in enumerate(sessions.sessions)]) for p in self.papers}
        self._prune_sac_coi(options)
        max_success = len(self.papers)

        # Assign papers until done or no more possible.
        tmp = 0
        while options:
            # Select and pop a paper.
            paper_no = self._select_from_options(options)
            paper_options = options.pop(paper_no)
            if not paper_options:
                # No more feasible options.
                max_success = max_success -1
                if max_success < self._best_score.num_papers:
                    break
                continue

            # Assign the paper to a session.
            sess_id = self._assign_paper(paper_no, paper_options, sessions)

            # Add the paper to the session.
            session = sessions.get(sess_id)
            session.papers.add(paper_no)
            session.acs.update(self.ac_assignments[paper_no])

            # Update all remaining options gie nthe new assignment.
            self._prune_paper_options(sessions, options, paper_no, sess_id)
        return sessions    


    def _is_better(self, current: Score, best: Score):   
        """
        Check if the current solution is better than the best solution.
        """
        if current.num_papers > best.num_papers:
            return True
        if current.num_papers < best.num_papers:
            return False
        if current.num_secondary_acs > best.num_secondary_acs:
            return True
        if current.num_secondary_acs < best.num_secondary_acs:
            return False
        # If the number of papers and secondary acs are the same, check the score.
        return current.energy > best.energy
        

    def _run_iteration(self, iteration):
        """
        Run a single iteration of the matching algorithm.
        """
        # Create an initial assignment of papers to sessions.
        sessions = self._match_papers()
        score = self.Score()

        # Prioritize assigning as many papers as possible. Can stop if that is not met.
        score.num_papers = sessions.total_papers()
        if score.num_papers < self._best_score.num_papers:
            return

        # Assign secondary acs to the papers.
        secondary_acs = {}
        if self.assign_secondary_acs:
            secondary_acs = self._assign_secondary_acs(sessions)
            score.num_secondary_acs = len(secondary_acs)
            # Second prioritize the number of secondary acs assigned. Can stop if that is not met.
            if score.num_secondary_acs < self._best_score.num_secondary_acs and score.num_papers == self._best_score.num_papers:
                return            
        
        # Assign the remaining ACs to sessions.
        self._assign_remaining_acs(sessions)

        # Compute the final score.
        score.energy = self.energy_fn(sessions, secondary_acs)
        if not self._is_better(score, self._best_score):
            return 
        
        # Update the best solution.
        self._best_solution = (sessions, secondary_acs)
        self._best_score = score
        self._stats[iteration] = score


    def _save_checkpoint(self):
        """
        Save a checkpoint of the current state.
        """
        if self.checkpoint_file:
            with open(self.checkpoint_file, "wb") as f:
                pickle.dump((self._best_solution, self._stats), f)


    def solve(self):
        """
        Create breakout groups and secondary ac assignments based on the given data.
        """
        # Verify the configuration and problem setup.
        self._verify_config()
        self._verify_problem()
        if self.num_threads <= 1:
            self._solve(with_ui=True)
        else:
            self._solve_threaded()
        return self._best_solution

    
    def _solve(self, with_ui, checkpoint_suffix=None):
        """
        Solve the matching problem in a single thread.
        """
        # Track the best solution. Number of papers assigned and number of secondary acs assigned is always prioritized since these are constraints.
        self._best_solution = None
        self._best_score = self.Score()
        self._stats = {}
        iteration = 0
        if checkpoint_suffix:
            self.checkpoint_file = self.checkpoint_file + checkpoint_suffix

        # Run through all iterations.
        for _ in tqdm(range(self.num_iterations), desc="Optimizing", unit="it") if with_ui else range(self.num_iterations):
            try:
                iteration = iteration + 1
                self._run_iteration(iteration)
                
                # Checkpointing.
                if self.checkpoint_num_it and iteration % self.checkpoint_num_it == 0:
                    self._save_checkpoint()

            except KeyboardInterrupt:
                # Exit gracefully from Keyboard Interrupt.
                print(f"Optimization stopped after {iteration} iterations: Keyboard Interrupt.")
                break 

        # Update the final stats and checkpoint.
        self._stats[iteration] = self._best_score
        self._save_checkpoint()

    def _thread_fn(self, queue, thread_id):
        self._solve(with_ui=False, checkpoint_suffix=f"_{thread_id}")
        queue.put((self._best_solution, self._best_score, self._stats))

    def _solve_threaded(self):
        processes = []
        queue = mp.Queue()
        for i in range(self.num_threads-1):
            # This should copy the object so this is fine.
            p = mp.Process(target=self._thread_fn, args=(queue,i+1))
            processes.append(p)
            p.start()

        # Run the main thread with ui.
        self._solve(with_ui=True, checkpoint_suffix="_0")

        # Wait for all threads to finish. and collect the results.
        for i, p in enumerate(processes):
            print(f"Waiting for thread {i+2}/{self.num_threads} to finish...", end="\r")
            sol, score, stats = queue.get()
            if self._is_better(score, self._best_score):
                self._best_solution = sol
                self._best_score = score
            self._join_stats(stats)
        print(" " * 50, end="\r")
        print(f"All {self.num_threads} threads finished.")


    def _join_stats(self, stats): 
        """
        Update the current stats with new stats from a parallel thread.
        """
        for it, score in stats.items():
            if it not in self._stats:
                self._stats[it] = score
            else:
                if self._is_better(score, self._stats[it]):
                    self._stats[it] = score  
        self._stats = dict(sorted(self._stats.items(), key=lambda x: x[0]))
        best = self.Score()
        for it in list(self._stats.keys()):
            if self._is_better(self._stats[it], best):
                best = self._stats[it]
            else:
                del self._stats[it]
        

    def get_optimization_stats(self):
        """
        Return the optimization stats from the last solve.
        """
        return self._stats


    def _initialize_ac_options(self, sessions: Sessions):
        """
        Compute which ACs could be assigned to each paper.
        """
        # Which sessions an AC can be assigned to.
        ac_options = {sess_id: self.all_acs for sess_id in range(len(sessions.sessions))}

        for sess_id, session in enumerate(sessions.sessions):
            # Max number of acs per session.
            if len(session.acs) >= session.max_num_acs:
                ac_options[sess_id] = set()
                continue

            # Time conflict: prune all ACs that are already assigned to a session.
            session_indices = sessions.indices_for_session(sess_id)
            for idx in session_indices:
                ac_options[idx] = ac_options[idx].difference(session.acs)
        
            # CoI: prune all ACs that have a CoI with the session.
            for paper in session.papers:
                ac_options[sess_id] = ac_options[sess_id].difference(self.conflicts[paper])

        return ac_options
    

    def _initialize_paper_options(self, sessions: Sessions):
        # Which ACs can be assigned to each paper. ACs already in the session have no conflict.
        paper_options = {}

        ac_options = self._initialize_ac_options(sessions)
        for sess_id, session in enumerate(sessions.sessions):
            for paper in session.papers:
                opt = ac_options[sess_id].union(session.acs)
                paper_options[paper] = opt - self.ac_assignments[paper]

        return paper_options
            
        
    def _assign_secondary_acs(self, sessions: Sessions):
        """
        Assign a secondary AC to each paper, such that the sessions remain feasible and the affinities are maximized.
        :param sessions: Sessions object containing session data.
        """
        # For now greedily assign the secondary ACs.
        secondary_acs = {}
        load = {ac: 0 for ac in self.all_acs}
        options = self._initialize_paper_options(sessions) # Which ACs can be assigned to each paper.
        max_success = len(self.papers)
        paper_to_session = {paper: sess_id for sess_id, session in enumerate(sessions.sessions) for paper in session.papers}

        # Assign papers until done.
        while options:
            # Select and pop a paper.
            paper_no = self._select_from_options(options)
            paper_options = options.pop(paper_no)
            if len(paper_options) == 0:
                # No more feasible options.
                max_success = max_success - 1
                if max_success < self._best_score.num_secondary_acs:
                    break
                continue

            # Assign the paper to a session.
            sess_id = paper_to_session[paper_no]
            session = sessions.get(sess_id)
            ac = None
            if self.second_ac_greedy:
                scores = {ac: self.affinities[paper_no].get(ac,0) for ac in paper_options}
                ac = max(scores, key=scores.get)
            else:
                ac = random.choice(list(paper_options))

            # Update AC load and assignment.
            secondary_acs[paper_no] = ac
            load[ac] += 1
            if load[ac] >= self.secondary_ac_max_load:
                for o in options.values():
                    o.discard(ac)

            # Add AC to the session.
            if ac in session.acs:
                # Already assigned to the session.
                continue

            session.acs.add(ac)

            # Remove the AC from time conflicts.
            conflicting_papers = set()
            for idx in sessions.indices_for_session(sess_id):
                if idx == sess_id:
                    continue
                conflicting_papers.update(sessions.get(idx).papers)
            for p in conflicting_papers:
                if p in options:
                    options[p].discard(ac)
        return secondary_acs
    

    def _assign_remaining_acs(self, sessions: Sessions):
        """
        Assign the remaining ACs to the sessions.
        """
        num_sessions = {ac : 0 for ac in self.all_acs}
        for session in sessions.sessions:
            for ac in session.acs:
                num_sessions[ac] += 1
        session_options = self._initialize_ac_options(sessions)

        # Which sessions an AC could be assigned to.
        ac_options = {ac : set([s for s, acs in session_options.items() if ac in acs]) for ac in self.all_acs}
        ac_options = {k: v for k, v in ac_options.items() if len(v) > 0}

        # Try to assign ACs such that everyone has some sessions to participate in.
        while ac_options:
            min_assigned = min([num_sessions[k] for k in ac_options])
            candidates = [ac for ac in ac_options if num_sessions[ac] == min_assigned]
            # Among the candidates, select the one with the fewest options.
            ac = min(candidates, key=lambda k: len(ac_options[k]))
            options = ac_options[ac]

            # Assign the AC to a session.
            sess_id = random.choice(list(options))
            session = sessions.get(sess_id)
            session.acs.add(ac)
            num_sessions[ac] += 1

            # Prune options.
            ac_options[ac] = options - set(sessions.indices_for_session(sess_id))
            if len(session.acs) >= session.max_num_acs:
                for opt in ac_options.values():
                    opt.discard(sess_id)
            ac_options = {k: v for k, v in ac_options.items() if len(v) > 0}