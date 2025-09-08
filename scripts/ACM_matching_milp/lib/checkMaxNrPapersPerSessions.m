function [] = checkMaxNrPapersPerSessions(Y)

for k=1:size(Y,1) % for each paper
    y = Y(k,:);
    assert( norm(y - round(y),'inf')<1e-6 )
    assert( isscalar(find(round(y)==1)) )
end