#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>

char const * const trueFlag = "\033[32mpassed\033[0m";
char const * const falseFlag = "\033[31mfailed\033[0m";
char const * const darkColorPrefix = "\033[38;2;128;128;128m";

bool g_summary_hooked = false;
size_t g_current_test_count = 0;
size_t g_current_passed_count = 0;
size_t g_current_failed_count = 0;
size_t g_total_test_count = 0;
size_t g_total_passed_count = 0;
size_t g_total_failed_count = 0;

void
report_integer_test(
    char const * const testedName,
    char const * const invokerName,
    char const * const fileName,
    int const lineNumber,
    int const value,
    int const expected,
    bool const isVerbose
) {
    bool isFailed = (false == (value == expected));
    if (isVerbose || isFailed) {
        printf(
                "Test [%s], testing value[ %s ]: %d, expected: %d\n",
                isFailed ? falseFlag : trueFlag,
                testedName,
                value,
                expected
        );
        if (isFailed) {
            printf(
                    "%s    Invoked at %s (%d) (%s)\033[0m\n",
                    darkColorPrefix,
                    fileName,
                    lineNumber,
                    invokerName
            );
        }
    }
    ++g_current_test_count;
    if (isFailed) {
        ++g_current_failed_count;
    } else {
        ++g_current_passed_count;
    }
}

void
setup_test_suite()
{
    g_current_test_count = 0;
    g_current_passed_count = 0;
    g_current_failed_count = 0;
    printf("\033[42m\033[30m====>>> Ready for test cases.\033[0m\n");
}

void
p_report_test_summary() {
    printf("\033[42m\033[30m[Test summary]\033[0m ");
    printf(
            "Total count: %lu; passed test count: \033[32m%lu\033[0m; "
            "failed test count: \033[31m%lu\033[0m.\n",
            g_total_test_count,
            g_total_passed_count,
            g_total_failed_count
    );
}

void
report_test_suite()
{
    if (false == g_summary_hooked) {
        atexit(p_report_test_summary);
        g_summary_hooked = true;
    }
    printf(
            "Total count: %lu; passed test count: \033[32m%lu\033[0m; "
        "failed test count: \033[31m%lu\033[0m.\n",
            g_current_test_count,
            g_current_passed_count,
            g_current_failed_count
    );
    g_total_test_count += g_current_test_count;
    g_total_passed_count += g_current_passed_count;
    g_total_failed_count += g_current_failed_count;
}
