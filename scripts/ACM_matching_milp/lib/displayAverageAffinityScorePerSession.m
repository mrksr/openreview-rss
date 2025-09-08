function [] = displayAverageAffinityScorePerSession(X,Y,A)

s = size(X,2);
aaps = zeros(s,1);
for j=1:size(Y,2) % for each session
    ind_papers = find(Y(:,j)==1);
    if length(ind_papers)>=1
        ind_ACs = find(X(:,j)==1);
        session_affinities = A(ind_ACs,ind_papers);
        aaps(j) = mean( session_affinities(:) );
    end
end
fprintf('Average Affinity Score Per Session:\n ')
disp(aaps')
