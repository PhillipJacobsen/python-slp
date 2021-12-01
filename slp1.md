# SLP1 contract descriptions

Action|#|Smart contract equivalent
-|-|-
GENESIS|0|Create a new token contract
BURN|1|Destroy/Burn tokens from a contract
MINT|2|Create/Mint tokens into a contract
SEND|3|Send tokens from sender address to recipient address
PAUSE|4|Pause the contract and prevents any call other than RESUME
RESUME|5|Resume the contract
NEWOWNER|6|change the owner of the contract
FREEZE|7|Freeze balance for token specific wallet
UNFREEZE|8|UnFreeze balance for token wallet

<!-- **SLP2**
Action|#|NFT equivalent
-|-|-
GENESIS|0|Create a new token
PAUSE|4|Pause the contract and prevents any call other than RESUME
RESUME|5|Resume the contract
NEWOWNER|6|Change the owner of the contract
AUTHMETA|9|Authorize a wallet to add metadata
REVOKEMETA|10|Revoke authorization to add metadata
ADDMETA|11|Add metadata to a contract
VOIDMETA|12|Mark a previously added metadata as void
CLONE|13|Create new token by cloning this contract information -->

## `GENESIS` contract

tb|GENESIS|-
-|-|-
de|decimals
qt|global supply
sy|token symbol
na|token name
du|document URI|optional
no|notes|optional
pa|pausable ?|default=False
mi|mintable ?|default=False

This contract does not need of concensus because it is just matter of parameter checks.

**On contract proposition:**
  1. decimal in [0..8] ?
  2. quantity * (10^decimal) < max unsigned long long ?
  3. symbol size in [3..8] ?
  4. name not exists ?
  5. name size in [3..24] ?
  6. document URI size in [0..32] ?
  7. notes size in [0..32] ?
  > Send back an orphan transaction with appropriate smartbridge, `GENESIS_AMOUNT` `amount` and `MASTER` `recipientId`.

**On finalized transaction reception:**
  > Broadcast finalized transaction to blockchain
  > The wallet issuing the transaction becomes `OWNER`
  > If not mintable, quantity is attributed to `OWNER`

## SLP1 `BURN` contract

tb|BURN|-
-|-|-
id|token id
qt|quantity
no|notes|optional

**On contract proposition:**
  1. token id exists?
  2. token not frozen ?
  3. quantity <= `OWNER.amount`?
  4. no decimals to quantity ?
  > **concensus needed**
  > send back an orphan transaction with appropriate smartbridge, `FUNGIBLE_AMOUNT` `amount` and `MASTER` `recipientId`.

**On finalized transaction reception:**
  1. `senderId` is token `OWNER`?
  > Broadcast finalized transaction to blockchain

## SLP1 `MINT` contract

tb|MINT|-
-|-|-
id|token id
qt|quantity
no|notes|optional

**On contract proposition:**
  1. token id exists?
  2. token mintable?
  3. token not frozen?
  4. no decimals to quantity?
  5. quantity + burned token + offchain token `<=` global supply?
  > **concensus needed**
  > send back an orphan transaction with appropriate smartbridge, `FUNGIBLE_AMOUNT` `amount` and `MASTER` `recipientId`.

**On finalized transaction reception:**
  1. `senderId` is token `OWNER`?
  > Broadcast finalized transaction to blockchain

## SLP1 `SEND` contract

tb|SEND|-
-|-|-
id|token id
qt|quantity
no|notes|optional

**On contract proposition:**
  1. token id exists ?
  2. token not frozen ?
  3. quantity decimals match?
  > **concensus needed**
  > send back an orphan transaction with appropriate smartbridge, `FUNGIBLE_AMOUNT` `amount` and `ADDRESS` `recipientId`.
 
**On finalized transaction reception:**
  1.  quantity  `<=` `WALLET` `amount` ?
  > Broadcast finalized transaction to blockchain