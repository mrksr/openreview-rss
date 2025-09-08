
class Session:
    """
    This class represents a single session in the AC meeting.
    """
    def __init__(self, papers=None, acs=None, sacs=None, max_num_papers=0, max_num_acs=0):
        self.papers = set(papers) if papers else set()
        self.acs: set = set(acs) if acs else set()
        self.sacs: set = set(sacs) if sacs else set()
        self.max_num_papers = max_num_papers
        self.max_num_acs = max_num_acs

    def copy(self):
        """
        Create a deep copy of the session.
        """
        return Session(papers=self.papers.copy(), acs=self.acs.copy(), sacs=self.sacs.copy(), max_num_papers=self.max_num_papers, max_num_acs=self.max_num_acs)

    
class Sessions:
    """
    This class represents the breakout sessions for the AC meeting.
    """

    def __init__(self, num_sessions, sacs, max_num_papers_per_session=0, max_acs_per_session=0):
        """
        Initialize the Sessions class.
        :param num_sessions: Number of sessions sequential sessions.
        :param sacs: List of SACs. Each SAC will lead a breakout group during each session.
        :param max_num_papers_per_session: Maximum number of papers per session. single value for all sessions or list of values for each session.        
        """
        self.num_sessions = num_sessions # Number of time slots
        self.sacs = list(sacs)
        self.num_sacs = len(sacs)
        num_total_sessions = num_sessions * self.num_sacs
        if not isinstance(max_num_papers_per_session, list):
            max_num_papers_per_session = [max_num_papers_per_session] * num_total_sessions
        assert len(max_num_papers_per_session) == num_total_sessions, "max_num_papers_per_session must be a single value or a list of values for each session."
        if not isinstance(max_acs_per_session, list):
            max_acs_per_session = [max_acs_per_session] * num_total_sessions
        assert len(max_acs_per_session) == num_total_sessions, "max_acs_per_session must be a single value or a list of values for each session."
        # Linear indexing of sessions in column-major order.
        self.sessions = [Session(sacs=[sac]) for sac in sacs for _ in range(num_sessions)]
        for i, session in enumerate(self.sessions):
            session.max_num_papers = max_num_papers_per_session[i]
            session.max_num_acs = max_acs_per_session[i]

    def idx_from_keys(self, sac, session_no):
        """
        Get the index of a session from the SAC and session ID.
        :param sac: SAC ID.
        :param session_no: Session number.
        :return: Index of the session.
        """
        return self.sacs.index(sac) * self.num_sessions + session_no
    
    def keys_from_idx(self, idx):
        """
        Get the SAC and session number from the index.
        :param idx: Index of the session.
        :return: Tuple of (SAC, session number).
        """
        session_no = idx % self.num_sessions
        sac = self.sacs[idx // self.num_sessions]
        return sac, session_no
    
    def indices_for_sac(self, sac):
        """
        Get the indices of all sessions for a given SAC.
        :param sac: SAC ID.
        :return: List of indices of sessions for the given SAC.
        """
        sac_idx = self.sacs.index(sac) * self.num_sessions
        return [i + sac_idx for i in range(self.num_sessions) ]
    
    def indices_for_session(self, session_no_or_id):
        """
        Get the indices of all sessions for a given session number.
        :param session_no: Session numberor id.
        :return: List of indices of sessions for the given session number.
        """
        session_no_or_id = session_no_or_id % self.num_sessions
        return [i * self.num_sessions + session_no_or_id for i in range(self.num_sacs)]

    def max_papers(self, session_id):
        """
        Return the maximum number of papers for a given session.
        :param session_id: Linear index of the sessions.
        """
        return self.sessions[session_id].max_num_papers
    
    def max_acs(self, session_no):
        """
        Return the maximum number of ACs for a given session.
        :param session_id: Linear index of the sessions.
        """
        return self.sessions[session_no].max_num_acs
    
    def max_total_papers(self):
        """
        Return the maximum number of papers for all sessions.
        """
        return sum([sess.max_num_papers for sess in self.sessions])
    
    def max_total_acs(self):
        """
        Return the maximum number of ACs for all sessions.
        """
        return sum([sess.max_num_acs for sess in self.sessions])

    def total_papers(self):
        """
        Return the total number of papers assigned to all sessions.
        """
        return sum([len(sess.papers) for sess in self.sessions])
    
    def total_acs(self):
        """
        Return the total number of ACs assigned to all sessions.
        """
        return sum([len(sess.acs) for sess in self.sessions])
    
    def total_sacs(self):
        """
        Return the total number of SACs assigned to all sessions.
        """
        return sum([len(sess.sacs) for sess in self.sessions])

    def get_by_key(self, sac, session_no) -> Session:
        """
        Get an individual session by SAC and session number.
        """
        return self.sessions[self.idx_from_keys(sac, session_no)]
    
    def get(self, idx) -> Session:
        """
        Get an individual session by index.
        """
        return self.sessions[idx]
    
    def copy(self):
        """
        Create a deep copy of the sessions.
        """
        new_sessions = Sessions(self.num_sessions, self.sacs)
        new_sessions.sessions = [s.copy() for s in self.sessions]
        return new_sessions


    def add_standout_session(self, all_acs):
        """
        Add a final standout sessions with all ACs that were not assigned to any session.
        """
        self.sacs.append("Standout")
        self.num_sacs += 1
        for i in range(self.num_sessions):
            new_session = Session(acs=all_acs)
            for sac in self.sacs[:-1]:
                new_session.acs.difference_update(self.get_by_key(sac, i).acs)
            self.sessions.append(new_session)

    def reorder_sacs(self, new_sacs):
        """
        Reorder the sessions based on the new SAC order.
        :param new_sacs: list of new SACs in correct order.
        """
        assert len(new_sacs) == self.num_sacs, "Number of new SACs must match the number of existing SACs."
        assert len(set(new_sacs) & set(self.sacs)) == self.num_sacs, "New SACs must be a the same existing SACs."
        old_sessions = self.sessions.copy()
        old_indices =[self.indices_for_sac(sac) for sac in new_sacs]
        self.sacs = new_sacs
        for i, new_sac in enumerate(self.sacs):
            for old, new in zip(old_indices[i], self.indices_for_sac(new_sac)):
                self.sessions[new] = old_sessions[old]
        

        
        