function [A,P,S,C]=syntheticInputs(n,s,p)

% id1_to_AC_name % only to display results
% id2_to_PaperID % only to display results

% A = id1_AC_vs_id2_PaperID_affinity
A = abs(rand(n,p)); 
A(:,9) = zeros(n,1); % "standout" sessions have zero affinity
A(:,18) = zeros(n,1); % "standout" sessions have zero affinity
A(:,27) = zeros(n,1); % "standout" sessions have zero affinity
A(:,36) = zeros(n,1); % "standout" sessions have zero affinity

% P = id1_AC_vs_id2_PaperID_primaryAC
P = eye(n,p);

% S = id1_AC_vs_id2_PaperID_secondaryAC
S = zeros(n,p); % no secondary ACs for now % [zeros(n,1) eye(n,p-1)];

% C = id1_AC_vs_id2_PaperID_COI
C = zeros(n,p);
num_COI = 30;
indices = randperm(n*p, num_COI);
[row_indices, col_indices] = ind2sub([n, p], indices);
C(sub2ind([n, p], row_indices, col_indices)) = 1;
C = C .* (ones(n,p)-P); % make sure there are no COI with the primary AC
C = C .* (ones(n,p)-S); % make sure there are no COI with the secondary AC