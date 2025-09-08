function [] = checkCOI(X,Y,C)

for i=1:size(C,1)
    for k=1:size(C,2)
        if C(i,k)==1 % if there is a COI
            y = Y(k,:);
            roundy = round(y);
            assert( norm(y - roundy,'inf')<1e-6 )
            j = find(roundy); % session where the paper is
            if length(j)~=1
                i,k
                j
                error('a paper has been assigned to none or multiple sessions')
            else
                assert(X(i,j)==0) % make sure the AC is not assigned to that session
            end
        end
    end
end