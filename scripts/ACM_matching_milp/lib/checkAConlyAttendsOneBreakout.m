function [] = checkAConlyAttendsOneBreakout(X)

n = size(X,1);
for i=1:n % for each AC
    x = X(i,:); 
    xround = round(x);
    assert( norm(x - xround,'inf')<1e-6 )
    assert( isscalar(find(xround(1:9)==1)) )
    assert( isscalar(find(xround(10:18)==1)) )
    assert( isscalar(find(xround(19:27)==1)) )
    assert( isscalar(find(xround(28:36)==1)) )
end