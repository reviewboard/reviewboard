diff -rN orig_src/foo.c new_src/foo.c
0a1,2
> #include <stdio.h>
> 
4c6,7
< 	printf("foo\n");
---
> 	printf("foo bar\n");
> 	return 0;
