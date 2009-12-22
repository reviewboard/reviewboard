@interface MyClass : Object
- (void) sayHello;
@end

@implementation MyClass
/*
 * Prints Hello world!
 */
- (void) sayHello
{
	printf("Hello world!");
}
@end
