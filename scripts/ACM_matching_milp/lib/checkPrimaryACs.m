function [] = checkPrimaryACs(X,Y,P)

for i=1:size(P,1)
    for k=1:size(P,2)
        if P(i,k)==1 % for each primary AC to paper match
            j = find(Y(k,:)); % session where the paper is
            if length(j)~=1
                error('a paper has been assigned to none or multiple sessions')
            else
                assert(X(i,j)==1) % make sure the AC is assigned to that session
            end
        end
    end
end