function [] = check_secondaryACs(S,P,C)

for i=1:size(C,1)
    for k=1:size(C,2)
        if C(i,k)==1 % if there is a COI
            assert(S(i,k)==0) % make sure the AC is not assigned to that paper
        end
        if P(i,k)==1 % if i is primary AC for that paper
            assert(S(i,k)==0) % make sure the AC is not assigned to that paper
        end
    end
end