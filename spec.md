
  > This is a reflexion about concensus around Side Level Protocol developped on Qredit blockchain. Purpose here is to evaluate the actions that have to be done so SLP networt could act as a side-blockchain. The porpose of this documentation is to maximize abstraction level of SLP so it can run with any blockchain where a smrtbridge can be embeded in a transaction.

# Definitions and rationales

  - **journal**: contract database updated according to smartbridges
  - **global supply**: maximum allowed token for a contract
  - **onchain token**: free token + circulating token - burned token - offchain token
  - **circulating token**: token from all wallets except `OWNER`
  - **offchain token**: cross exchanged token
  - **free token**: undistributed token
  - `OWNER` only owns free token
  - minted token + abs(burned token) + offchain token  `<=` **global supply**

# Journal

  - `DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA` creates and owns contract `aabe476e47b1cc79e7868ddbce0d0aee`
  - `DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA` mints `85` token
  - `DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA` sends `10.5` token to `DMzBk3g7ThVQPYmpYDTHBHiqYuTtZ9WdM3`
  - `DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA` burns `27` token
  - `DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA` cross exchanges `20` token with another SLP blockchain
  - another SLP blockchain cross exchanges back `9.5` token to `DJDypKeHGeLHNdHdDThsgVQhFHicUG6SVf`
  - `DJDypKeHGeLHNdHdDThsgVQhFHicUG6SVf` sends `9.5` token to `DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA`

**Records**

timestamp|tx|id|nok|tp|de|sy|na|du|qt|no|pa|mi
-|-|-|-|-|-|-|-|-|-|-|-|-
1638264520|_blockchainTxId_|||GENESIS|2|TTK|Test Token||150000||True|True
1638265720|_blockchainTxId_|aabe476e47b1cc79e7868ddbce0d0aee||MINT|||||85.00
**1638265815**|**blockchainTxId**|**aabe476e47b1cc79e7868ddbce0d0aee**||**SEND**|||||**10.50**
1638265973|_blockchainTxId_|aabe476e47b1cc79e7868ddbce0d0aee||BURN|||||27.00
1638266083|_blockchainTxId_|aabe476e47b1cc79e7868ddbce0d0aee||CCXO|||||20.00|_altBlockchainAddress_
1638267582|_alt_BlockchainTxId_|aabe476e47b1cc79e7868ddbce0d0aee||CCXI|||||9.5|_DJDypKeHGeLHNdHdDThsgVQhFHicUG6SVf_
**1638267817**|**blockchainTxId**|**aabe476e47b1cc79e7868ddbce0d0aee**||**SEND**|||||**9.5**

**Contract**: a unique and immutable line per contract.

timestamp|id|type|name|symbol|global supply|decimals|notes|document URI|pausable|mintable
-|-|-|-|-|-|-|-|-|-|-
1638264520|aabe476e47b1cc79e7868ddbce0d0aee|slp1|Test token|TTK|150000|2|||True|True

**Owners**

timestamp|id|type|address
-|-|-|-
1638264520|aabe476e47b1cc79e7868ddbce0d0aee|slp1|DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA

**Metadata**

timestamp|id|address|data
-|-|-|-

**Accountings**

timestamp|id|address|exchanged|crossed|minted|burned
-|-|-|-|-|-|-
1638265720|aabe476e47b1cc79e7868ddbce0d0aee|DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA|||85.00
**1638265815**|**aabe476e47b1cc79e7868ddbce0d0aee**|**DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA**|**-10.50**
**1638265815**|**aabe476e47b1cc79e7868ddbce0d0aee**|**DMzBk3g7ThVQPYmpYDTHBHiqYuTtZ9WdM3**|**10.50**
1638265973|aabe476e47b1cc79e7868ddbce0d0aee|DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA||||-27.00
1638266083|aabe476e47b1cc79e7868ddbce0d0aee|DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA||-20.00
1638267582|aabe476e47b1cc79e7868ddbce0d0aee|DJDypKeHGeLHNdHdDThsgVQhFHicUG6SVf||9.50
**1638267817**|**aabe476e47b1cc79e7868ddbce0d0aee**|**DJDypKeHGeLHNdHdDThsgVQhFHicUG6SVf**|**-9.50**
**1638267817**|**aabe476e47b1cc79e7868ddbce0d0aee**|**DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA**|**9,50**

## Journal state

Even if SQL allow fast computation on stored data, it is interesting to compute a database state on node start and increment it on each contract execution.

**Supply state**:
id|owner|free|circulating|paused
-|-|-|-|-

**User state**:
address|id|balance|frozen|authmeta
-|-|-|-|-

## SQL glimpse

**Free token**:
```SQL
SELECT SUM(exchanged, crossed, minted, burned) FROM accountings
WHERE address IN (
    SELECT address FROM owners WHERE id='aabe476e47b1cc79e7868ddbce0d0aee'
) AND id='aabe476e47b1cc79e7868ddbce0d0aee';
```
**Circulating token**:
```SQL
SELECT SUM(exchanged, crossed) FROM accountings
WHERE address NOT IN (
    SELECT address FROM owners WHERE id='aabe476e47b1cc79e7868ddbce0d0aee'
) AND id='aabe476e47b1cc79e7868ddbce0d0aee';
```
**Available token**:
```SQL
SELECT SUM(minted, burned, crossed) FROM accountings
WHERE id='aabe476e47b1cc79e7868ddbce0d0aee';
```
**Balances**:
```SQL
SELECT address, SUM(exchanged, crossed, minted, burned) FROM accountings
WHERE id='aabe476e47b1cc79e7868ddbce0d0aee';
```

# Node concensus

## Relays and validators?

One can consider two types of nodes in SLP ecosystem
  1. validators: nodes runing on a blockchain peer ie with blockchain database access
  2. relays: stand alone running nodes

## SLP contract validation

2 steps are needed to validate an SLP contract:
  - on contract proposition: 
    + wallet issuing the contract is not known yet
    * need concensus to validate contract proposition
    * return an orphan transaction with SLP contract as `vendorField`
  - on finalized transaction reception:
    + wallet issuing the contract is known
    * no concensus needed
    * broadcast transaction if it matches contract specification

## Concensus

on receiving SLP contract proposition:
  1. check if it matches locally
  2. broadcast to known validators with the last contract height
  3. validators answer `True` if accepted or `False` if refused with the asked height supply state hash: `sha256(id|owner|free|circulating|paused)`
  4. if corrum reached, return orphan transaction with SLP smartbridge

on receiving webhook data `transaction.applied`:
  1. deserialize smartbridge and check if it matches locally
  2. add deserialized smartbridge into record database with `nok=True` if error 
  3. apply the contract if `nok==False`
