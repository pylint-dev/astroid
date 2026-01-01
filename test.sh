#!/usr/bin/env bash
set -e

echo "Astroid version:"
python -c "from astroid import __pkginfo__; print(__pkginfo__.version)"
echo

echo "Running multiline #@ extraction test..."
echo

python - << 'EOF'
from astroid import builder

code = """
model = tf.keras.Sequential(layers=[
    tf.keras.layers.Dense(units=64, activation='relu'),
    tf.keras.layers.Dense(units=10)
])  #@
"""

node = builder.extract_node(code)

print("Extracted node type:", type(node))
print("Node repr:")
print(node)
print()
print("Start line:", getattr(node, "lineno", None))
print("End line:", getattr(node, "end_lineno", None))
EOF
