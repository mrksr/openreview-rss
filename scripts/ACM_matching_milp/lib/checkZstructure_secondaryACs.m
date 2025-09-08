function [] = check_Zstructure_secondaryACs(A,S,Z)

for i=1:size(A,1)
    for k=1:size(A,2)
        if(S(i,k)==1) % if selected
            assert(abs(A(i,k) - Z(i,k) )<1e-6)
        else
            assert(Z(i,k)<1e-6)
        end
    end
end