fileA = readtable(strcat(dataFolder,'A.csv'));
ACname = fileA.Var1(2:end,1);
try
    fileA_S = readtable(strcat(dataFolder,'A_S.csv'));
    SACname = fileA_S.Var1(2:end,1);
    ACname = [ACname; SACname];
catch exception
    fprintf('No SAC file found.\n')
end
PaperIDs = fileA{1,2:end};

for j=1:size(X,2) % for each session
    if j == 9 || j == 18 || j == 27 || j ==36
        fprintf('==================== \n Session: %d (standout) \n',j)
        for k = 1:p
            if Y(k,j)==1 % if paper is in that session
                error('There must be no papers in standout sessions!')
            end
        end

    else
        fprintf('==================== \n Session: %d \n',j)
        fprintf(' Papers in session: ')
        for k = 1:p
            if Y(k,j)==1 % if paper is in that session
                fprintf(' %d',PaperIDs(k));
            end
        end
    end
    fprintf('\n ACs in session: \n')
    for i = 1:n
        if X(i,j)==1 % if AC is in that session
            fprintf('%s \n',ACname{i});
        end       
    end
end