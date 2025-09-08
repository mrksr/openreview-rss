function [A,P,S,C,p]=parseInputs_withSACs(folder,useSecondaryACs)

A = csvread(strcat(folder,'A.csv'),1,1);
P = csvread(strcat(folder,'P.csv'),1,1);
if useSecondaryACs == 1
    S = csvread(strcat(folder,'S.csv'),1,1);
else
    S = zeros(size(P));
end
C = csvread(strcat(folder,'C.csv'),1,1);

p = size(C,2);

A_S = csvread(strcat(folder,'A_S.csv'),1,1);
P_S = zeros(size(A_S,1),p); 
S_S = zeros(size(A_S,1),p);
C_S = csvread(strcat(folder,'C_S.csv'),1,1);

% just concatenate and put SACs at the end
A = [A; A_S];
P = [P; P_S];
S = [S; S_S];
C = [C; C_S];
