 #!/bin/bash

echo 'path/name for the log file?'
read FILE_PATH

echo 'getblocktemplate:'
grep "BTC_BLOCK_RECEIVED_START" $FILE_PATH  | wc -l

echo 'BTC submits ALL:'
grep "BTC_SUBMITBLOCK" $FILE_PATH | wc -l

echo 'BTC submits ACCEPTED:'
grep "# Block" $FILE_PATH | grep "ACCEPTED" | wc -l

echo 'BTC submits REJECTED:'
grep "# Block" $FILE_PATH | grep "REJECTED" | wc -l

echo 'RSK submits ALL:'
grep "RSK_SUBMITBLOCK" $FILE_PATH | wc -l

echo 'RSK submits ACCEPTED:'
grep "Submit to RSK, Block ACCEPTED" $FILE_PATH | wc -l

echo 'Submit to RSK, Block FAIL:'
grep "Submit to RSK, Block FAIL" $FILE_PATH | wc -l

echo 'Shares:'
grep "SHARE_RECEIVED_START" $FILE_PATH | wc -l

echo "Errors ------------------" 
echo 'SUBMIT - Duplicate share:'
grep "SUBMIT EXCEPTION: Duplicate share" $FILE_PATH | wc -l