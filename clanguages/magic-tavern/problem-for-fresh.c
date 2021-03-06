/*
Problem for fresh

分值：1

程序执行时限: 1000 ms

题目描述：
这道题的主要目的是带你熟悉这个在线评测系统。你需要实现一个可执行程序，将来自标准输入的内容，原样输出到标准输出。在线评测系统将用系统内置的一些测试用例对你的程序进行评测。

输入：(这里对传给你的程序的输入格式进行说明)
一些字符串

输出：(这里对你的程序需要给出的输出格式进行说明)
与输入相同的字符串

约束：(这里对输入的字符和数字规模进行约束)
输入字符串仅包含大小写字母、数字、空格和标点符号，仅有一行

举例1：(这里是一些输入和期望输出的举例)
输入：
hello the world
输出：
hello the world

举例2：
输入：
hello world!
输出：
hello world!
*/

#include <stdio.h>

int main()
{
  char input[1024];
  scanf("%[^\n]", input);
  printf("%s\n", input);
  return 0;
}
