clear all
close all
clc
addpath('./lib')

maxTime = 8*3600; % maximum time we allow the optimization to run (8h)

%% read inputs
n = 54; 
s = 36;

% p = 168; % nr of papers to discuss
% [A,P,S,C]=syntheticInputs(n,s,p);

[A,P,S,C,p]=parseInputs('../../private/');
checkInputs(A,P,S,C);

maxPapersRegularSessions = 6;
maxPapersOverflowSessions = 3;
maxACRegularSessions = 9;
minACRegularSessions = 3;

a_max = 10; % in principle this is less than 1 x nr of papers in a session, which is <= maxPapersRegularSessions 
p_max = [maxPapersRegularSessions*ones(8,1);0;maxPapersRegularSessions*ones(8,1);0;maxPapersRegularSessions*ones(8,1);0;maxPapersOverflowSessions*ones(8,1);0];
n_max = [maxACRegularSessions*ones(8,1);n;maxACRegularSessions*ones(8,1);n;maxACRegularSessions*ones(8,1);n;maxACRegularSessions*ones(8,1);n];
n_min = [minACRegularSessions*ones(8,1);0;minACRegularSessions*ones(8,1);0;minACRegularSessions*ones(8,1);0;minACRegularSessions*ones(8,1);0];

%% Define auxiliary vectors and matrices
e_1_9 = zeros(s,1);   e_1_9(1:9)     = ones(9,1);
e_10_18 = zeros(s,1); e_10_18(10:18) = ones(9,1);
e_19_27 = zeros(s,1); e_19_27(19:27) = ones(9,1);
e_28_36 = zeros(s,1); e_28_36(28:36) = ones(9,1);

nx = 2*n*s + p*s; 
Is = eye(s);
In = eye(n);
Ip = eye(p);
ns = n*s;
ps = p*s;
EX = [eye(ns) zeros(ns,ps) zeros(ns,ns)];
EY = [zeros(ps,ns) eye(ps) zeros(ps,ns)];
EZ = [zeros(ns,ns) zeros(ns,ps) eye(ns)];

%%% define parameters for the x = intlinprog(f,intcon,A,b,Aeq,beq,lb,ub)
f = -ones(1,ns) * EZ;  % minus since we maximize
intcon = 1:ns+ps; % X and Y are binary

%% Equality constraints
Aeq = kron(e_1_9',In)*EX;
beq = ones(n,1);
Aeq = [Aeq; kron(e_10_18',In)*EX];
beq = [beq; ones(n,1)];
Aeq = [Aeq; kron(e_19_27',In)*EX];
beq = [beq; ones(n,1)];
Aeq = [Aeq; kron(e_28_36',In)*EX];
beq = [beq; ones(n,1)];
% each paper is assigned to a single session
Aeq = [Aeq; kron( ones(1,s) , Ip )*EY];
beq = [beq; ones(p,1)];

%% Inequality constraints
% constrain Z
Aineq = EZ-a_max*EX;
bineq = zeros(ns,1);
Aineq = [Aineq;   EZ-kron(Is,A)*EY];
bineq = [bineq; zeros(ns,1)];
% upper bound on the number of papers per session
Aineq = [Aineq;   kron(Is,ones(p,1)')*EY];
bineq = [bineq; p_max];
% primary AC
Aineq = [Aineq;  1/maxPapersRegularSessions * kron(Is,P)*EY - EX];
bineq = [bineq; zeros(ns,1)];
% secondary AC
Aineq = [Aineq;  1/maxPapersRegularSessions * kron(Is,S)*EY - EX];
bineq = [bineq; zeros(ns,1)];
% COI
Aineq = [Aineq;  EX + 1/maxPapersRegularSessions * kron(Is,C)*EY];
bineq = [bineq; ones(ns,1)];
% upper and lower bound on number of AC per session
Aineq = [Aineq;   kron(Is,ones(n,1)')*EX];
bineq = [bineq; n_max];
Aineq = [Aineq;   -kron(Is,ones(n,1)')*EX];
bineq = [bineq; -n_min];

%% upper and lower bounds
lb = zeros(nx,1);
ub = ones(nx,1); ub(ns+ps+1:end) = a_max * ones(ns,1); % large bound on Z

%% make all sparse
f = sparse(f);
Aineq = sparse(Aineq);
bineq = sparse(bineq);
Aeq = sparse(Aeq);
beq = sparse(beq);
lb = sparse(lb);
ub = sparse(ub);

%% solve
options = optimoptions('intlinprog','MaxTime',maxTime); 
[x,fval,exitflag,output] = intlinprog(f,intcon,Aineq,bineq,Aeq,beq,lb,ub,[],options);
cumulativeAffinityOfSolution = ones(1,ns) * EZ * x;

X = reshape(EX * x,n,s); 
Y = reshape(EY * x,p,s); 
Z = reshape(EZ * x,n,s); 

Xunrounded = X;
Yunrounded = Y;
X = round(X);
Y = round(Y);

%% display stats
displayAverageAffinityScorePerSession(X,Y,A)
fprintf('Nr of AC per session:\n ')
disp(sum(X))
fprintf('Nr of papers per session:\n ')
disp(sum(Y))
fprintf('Number of ACs in standout breakouts:\n %d, %d, %d, %d \n', sum(X(:,9)),sum(X(:,18)),sum(X(:,27)),sum(X(:,36)))

%% unit test: check constraint satisfaction:
checkZstructure(X,Y,Z,A);
checkCOI(X,Y,C);
checkPrimaryACs(X,Y,P);
checkPrimaryACs(X,Y,S);
checkMaxNrPapersPerSessions(Y);
checkAConlyAttendsOneBreakout(X);
checkMinMaxACPerSessions(X,minACRegularSessions,maxACRegularSessions);

csvwrite(strcat('../../private/X.csv'),X);
csvwrite(strcat('../../private/Y.csv'),Y);

filename = ['output_' datestr(now,'yyyy-mm-dd_HH_MM_SS') '.mat']
save(filename)