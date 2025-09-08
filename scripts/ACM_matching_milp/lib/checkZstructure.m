function [] = checkZstructure(X,Y,Z, Aff)

AC_vs_session_affinities = Aff * Y;
Zexpected = X .* AC_vs_session_affinities;

assert(norm(Z - Zexpected,'inf')<=1e-6)