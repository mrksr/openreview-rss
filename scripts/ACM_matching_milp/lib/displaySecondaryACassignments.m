fileA = readtable(strcat(dataFolder,'A.csv'));
ACname = fileA.Var1(2:end,1);
PaperIDs = fileA{1,2:end};

for i=1:size(S,1) % for each AC
    fprintf('%s: ',ACname{i});
    for k = 1:size(S,2)
        if S(i,k)==1 % if paper is assigned to AC i
            fprintf(' %d ',PaperIDs(k));
        end
    end
    fprintf('\n');
end