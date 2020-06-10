#include "board-test.h"

// ======= Temporary block for quick prototype.
#include <stdlib.h>
#include <stdio.h>
#include <time.h>

#include "testool.h"

/*
TODO
Design a dynamic indexer.
Design a expanding tree.
Implement Monte-Carlo tree search.
*/

typedef struct _Tree Tree;
typedef struct _Node Node;
typedef struct _NodeIndex NodeIndex;
typedef struct _NodeIndexSection NodeIndexSection;

struct _NodeIndexSection {
    Node * refs[10];
    NodeIndexSection * prevRef;
    NodeIndexSection * nextRef;
};

struct _NodeIndex {
    // This struct is a link list.
    int refCount;
    int sectionCount;
    NodeIndexSection initialSection;
};

struct _Node {
    NodeIndex const childrenIndex;
};

struct _Tree {
    Node * rootRef;
    NodeIndex const leafsIndex;
    int height;
    int nodeCount;
};

/*
TODO
Make the testtools with M_ style macro function have to be ended with semicolon.
Provide a non-pass-print M_test_int_npp macro function.

Design a index provider.
*/
#define M_table_index_count 225
typedef struct _IndexProvider {
    int count;
    int indexes[M_table_index_count];
} IndexProvider;

void
initIndexProvider(IndexProvider * const provider)
{
    provider->count = M_table_index_count;
    for (int i = 0; i < M_table_index_count; ++i) {
        provider->indexes[i] = i;
    }
}

bool
hasMoreIndex(IndexProvider const * const provider)
{
    return provider->count > 0;
}

void
_doRemoveIndex(IndexProvider * const provider, int const targetIndex)
{
    int lastIndex = provider->count - 1;
    provider->indexes[targetIndex] = provider->indexes[lastIndex];
    provider->count = lastIndex;
}

bool
removeIndex(IndexProvider * const provider, int const targetIndex)
{
    if (
        (targetIndex >= M_table_index_count) ||
        (targetIndex < 0)
    ) {
        return false;
    }
    //Debug:
    printf("Odd here ====>>> targetIndex: %d, provider->indexes[targetIndex]: %d.\n", targetIndex, provider->indexes[targetIndex]);
    if (
        (targetIndex == provider->indexes[targetIndex]) &&
        (targetIndex < provider->count)
    ) {
        if (1 == provider->count) {
            provider->count = 0;
        } else {
            _doRemoveIndex(provider, targetIndex);
        }
        return true;
    }
    for (int i = 0; i < provider->count; ++i) {
        if (targetIndex == provider->indexes[i]) {
            _doRemoveIndex(provider, i);
            return true;
        }
    }
    M_debug_line()
    return false;
}

/**
Have to check with hasMoreIndex(provider) before use provideIndex(provider).
May cause undefined behavior without checking.
*/
int
provideIndex(IndexProvider * const provider)
{
    // Generate random number, and convert to index.
    int targetIndex = rand() % provider->count;
    // Get the index.
    int resultIndex = provider->indexes[targetIndex];
    // Remove the index.
    if (false == removeIndex(provider, resultIndex)) {
        printf("[\033[31mError\033[0m] Failed to remove \
targetIndex( %d ) for \
IndexProvider( %p )\n",
            targetIndex,
            provider
        );
    }
    return resultIndex;
}

void
tryRandomNumber(void)
{
    printf("Random numner: [%d].\n", rand() % 100);
}

void
tryBuildTree(void)
{
    Tree tree = {
        .rootRef = malloc(sizeof(Node)),
        .leafsIndex = {
            .refCount = 0,
            .sectionCount = 1,
            .initialSection = {
                .prevRef = NULL,
                .nextRef = NULL,
            },
        },
        .height = 0,
        .nodeCount = 0,
    };
    printf("\
Hello tree! height: %d, nodeCount: %d,\n\
leafsIndex.sectionCount: %d, rootRef: %p,\n\
leafsIndex.initialSection[0]: %p,\n\
leafsIndex.initialSection[9]: %p.\n",
        tree.height, tree.nodeCount, tree.leafsIndex.sectionCount,
        tree.rootRef, tree.leafsIndex.initialSection.refs[0],
        tree.leafsIndex.initialSection.refs[9]
    );
}
// ======= Temporary block end.

int
main(void)
{
    srand(time(NULL)); // time(NULL) returns time in seconds.

    testBoardCheckers();

    // ======= Temporary block for quick prototype.
    tryRandomNumber();
    tryBuildTree();

    IndexProvider * const indexProvider = malloc(sizeof(IndexProvider));
    initIndexProvider(indexProvider);
    M_test_int(hasMoreIndex(indexProvider), true)
    M_test_int(removeIndex(indexProvider, 224), true)
    M_test_int(removeIndex(indexProvider, M_table_index_count), false)
    M_test_int(removeIndex(indexProvider, 250), false)
    M_test_int(removeIndex(indexProvider, -1), false)
    M_test_int(removeIndex(indexProvider, 0), true)
    M_test_int(indexProvider->count, 223)
    M_test_int(provideIndex(indexProvider) < 224, true)
    for (int i = 0; i < 222; ++i) {
        M_test_int(provideIndex(indexProvider) < 224, true)
        M_test_int(indexProvider->count, 221 - i)
    }
    // ======= Temporary block end.

    return 0;
}