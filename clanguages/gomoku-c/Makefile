args_c_standard = -std=c99
args_optimizers = -O2
args_includes = -Iinclude
args_warnings = -Wall

args_set = $(args_c_standard) $(args_optimizers) \
 	$(args_includes) $(args_warnings)

path_src = src
path_lib = lib
path_bin = bin

src_main = $(path_src)/main.c
app_path = $(path_bin)/main

sources := $(filter-out $(src_main),$(wildcard $(path_src)/*.c))
objects := $(sources:.c=.o)
objects := $(subst $(path_src)/,$(path_lib)/,$(objects))

combined_args = $(args_set) \
	$(objects) $(src_main) -o $(app_path)

all: test
	@echo 'Make start. [all] <<<===='
	$(CC) $(combined_args)
	@echo '====>>>> [all] Make done.'
.PHONY: all

$(objects): $(path_lib)/%.o: $(path_src)/%.c
	$(CC) $(args_set) -c $< -o $@

path_test = test
test_entrance_path = $(path_test)/main.c
test_sources := $(filter-out $(test_entrance_path),$(wildcard $(path_test)/*.c))
test_objects := $(test_sources:.c=.o)
test_objects := $(subst $(path_test)/,$(path_lib)/,$(test_objects))
test_bin_path = $(path_bin)/test
combined_args_for_test = $(CC) $(args_set) -I$(path_src) \
 	$(objects) $(test_objects) \
 	$(test_entrance_path) -o $(test_bin_path)
test: $(objects) $(test_objects)
	@echo 'Make start. [test] <<<===='
	$(combined_args_for_test)
	@echo '====>>>> [test] Make done.'
	@$(test_bin_path)
.PHONY: test

$(test_objects): $(path_lib)/%.o: $(path_test)/%.c
	$(CC) $(args_set) -I$(path_src) -c $< -o $@

clean:
	@rm lib/*
	@rm bin/*
.PHONY:clean
