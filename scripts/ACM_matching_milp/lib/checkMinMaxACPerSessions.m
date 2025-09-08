function [] = checkMinMaxACPerSessions(X,minACRegularSessions,maxACRegularSessions)

nrACperSession = sum(X);
nrACperRegularSession = nrACperSession([1:8,10:17,19:26,28:35]);
assert(min(nrACperRegularSession)>=minACRegularSessions)
assert(max(nrACperRegularSession)<=maxACRegularSessions)