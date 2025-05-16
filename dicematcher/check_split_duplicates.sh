#  check_split_duplicates.sh
#  --------------------------------------------------------------
#  Report validation images whose *contents* also live in train/.
#  Uses sha256 hashes for reliability but lets ripgrep do the set
#  intersection.
#
#  USAGE
#      bash check_split_duplicates.sh  [train_dir]  [val_dir]
#      # defaults:  train=new_dataset/train   val=new_dataset/valid
#
#  REQUIRES
#      • coreutils sha256sum
#      • ripgrep (rg)
#  --------------------------------------------------------------

set -euo pipefail
shopt -s lastpipe          # so while-loops inherit redirections

TRAIN_DIR="${1:-new_dataset/train}"
VAL_DIR="${2:-new_dataset/valid}"

EXT_REGEX='.*\.(jpg|jpeg|png|bmp|gif|tiff?)$'   # edit if needed

tmp_train=$(mktemp)
tmp_val=$(mktemp)

echo "🟢  hashing TRAIN images …"
find "$TRAIN_DIR" -type f | rg -i -e "$EXT_REGEX" -0 \
  | tr '\0' '\n' \
  | while IFS= read -r file; do
        sha256sum "$file"
    done > "$tmp_train"

echo "🔵  hashing VAL images …"
find "$VAL_DIR" -type f | rg -i -e "$EXT_REGEX" -0 \
  | tr '\0' '\n' \
  | while IFS= read -r file; do
        sha256sum "$file"
    done > "$tmp_val"

# --------------------------------------------------------------
# ripgrep magic:
#   1. feed *only hashes* from validation as patterns (stdin)
#   2. search those hashes in the train-hash file
#   3. -F   = fixed string (hashes are not regexes)
#   4. -f - = “patterns come from stdin”
# --------------------------------------------------------------
echo
echo "🔍  scanning for duplicates with rg …"
echo "--------------------------------------------------------------"

cut -d' ' -f1 "$tmp_val" | rg -F -f - "$tmp_train" \
| while read -r hash train_path; do
        # find the matching validation path(s)
        rg -F "$hash" "$tmp_val" | while read -r _ val_path; do
            echo "⚠️  DUPLICATE:"
            echo "    VAL  : $val_path"
            echo "    TRAIN: $train_path"
            echo
        done
done
# ------------------------------------------------------------------
#  DUPLICATE REDISTRIBUTION  (keep 60 % in train / 40 % in valid)
# ------------------------------------------------------------------
dups_file=$(mktemp)

# ➊  sort both hash-lists on the first field (hash)  ⬇⬇
sort -k1,1 "$tmp_train" -o "$tmp_train"
sort -k1,1 "$tmp_val"   -o "$tmp_val"

join -j 1 -o 1.1,1.2,2.2 "$tmp_val" "$tmp_train" > "$dups_file"

total_dups=$(wc -l <"$dups_file")
keep_train=$(( total_dups * 60 / 100 ))   # keep this many in TRAIN
keep_valid=$(( total_dups - keep_train )) # rest stay in VALID

echo
echo "🔀  Redistributing duplicates …"
echo "    total pairs : $total_dups"
echo "    keep in train: $keep_train"
echo "    keep in valid: $keep_valid"
echo "--------------------------------------------------------------"

shuf "$dups_file" | nl -ba | while read -r idx hash val_path train_path; do
    if (( idx <= keep_train )); then
        echo "train ✔︎ | valid ✗  : $(basename "$val_path")"
        rm -f -- "$val_path"                     # remove duplicate from VALID
    else
        echo "valid ✔︎ | train ✗  : $(basename "$train_path")"
        rm -f -- "$train_path"                   # remove duplicate from TRAIN
    fi
done

rm -f "$dups_file"  "$tmp_train"  "$tmp_val"
echo "✅  Redistribution done."

rm -f "$tmp_train" "$tmp_val"
echo "Done."
