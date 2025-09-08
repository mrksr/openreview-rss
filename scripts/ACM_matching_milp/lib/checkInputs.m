function checkInputs(A,P,S,C)

maxA = max(A(:));
assert(maxA>=0);
assert(maxA<=1);

for k=1:size(P,2) % for each paper
    assert( isscalar(find(P(:,k)==1)) ) % single primary AC
end

if ~isempty(S)
    for k=1:size(P,2) % for each paper
        assert( length(find(S(:,k)<=1)) ) % at most 1 secondary AC
    end
end