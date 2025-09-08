function [A,P,S,C,p]=parseInputs(folder)

A = csvread(strcat(folder,'A.csv'),1,1);
P = csvread(strcat(folder,'P.csv'),1,1);
S = zeros(size(P));
C = csvread(strcat(folder,'C.csv'),1,1);

p = size(C,2);