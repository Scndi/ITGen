# Copyright (c) Microsoft Corporation. 
# Licensed under the MIT license.

import os
from tree_sitter import Language, Parser

# 设置编译环境变量，确保使用 C11 标准（修复 static_assert 问题）
os.environ['CC'] = 'gcc'
os.environ['CFLAGS'] = '-std=c11 -D_GNU_SOURCE'

Language.build_library(
  # Store the library in the `build` directory
  'my-languages.so',

  # Include one or more languages
  [
    'tree-sitter-python',
    'tree-sitter-java',
    'tree-sitter-cpp',
    'tree-sitter-c',

  ]
)

