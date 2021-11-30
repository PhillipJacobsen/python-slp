**Side Ledger Protocol**

  > This is a reflexion about concensus around Side Ledger Protocol developped on Qredit blockchain. Purpose here is to evaluate the actions that have to be done so SLP networt could act as a side-blockchain. The porpose of this documentation is to maximize abstraction level of SLP so it can run with any blockchain where a smrtbridge can be embeded in a transaction.

# Definitions and rationales

## Smartbridge

Serialized information stored on `vendorField` of all ARK blockchain based transaction. `vendorFIeld` was the very first way ARK considered interoperability with other blockchain before the ARK logic concept. Because of `vendorField` size limitation, contract have to be normalized and serialized so maximum information can be broadcasted within one and single transaction.

## Contract

**SLP1**
Action|#|ERC-20 equivalent
-|-|-
GENESIS|0|Create a new token contract
BURN|1|Destroy/Burn tokens from a contract
MINT|2|Create/Mint tokens into a contract
SEND|3|Send tokens from sender address to recipient address
PAUSE|4|Pause the contract
RESUME|5|Resume the contract
NEWOWNER|6|change the owner of the contract
FREEZE|7|Freeze balance for token specific wallet
UNFREEZE|8|UnFreeze balance for token wallet

**SLP2**
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
CLONE|13|Create new token by cloning this contract information

## Contract fields and values

An input inside a contract is described with one action type and parameters. Because smartbridge size is limited (256 chars), type action and parameters name have to be reduced:

**Fileds**

name|description|type
-|-|-
tx|blockchain transaction id|hexadecimal
tp|type of action|string
id|token ID|hexidecimal
de|decimal places|short: 0..8
qt|quantity|unsigned long long
sy|symbol / ticker|string
na|token name|string
du|document URI|string (`ipfs://` scheme)
no|notes|string
pa|pausable|boolean: Default false
mi|mintable|boolean: Default false
ch|smartbridge chunck|short
dt|data|string
wt|blockchain wallet address|string
pk|blockchain public key|hexadecimal

Human readable representation of contract inputs is the well known JSON structure (135 chars):

```json
{"SLP1": {"tp":"GENESIS","de":8,"qt":100000,"sy":"TEST","na":"Token name","du":"https://test.com","no":"notes","pa":false,"mi":false}}
```

More advanced way is serialized one (80 chars):

```python
'slp1://0008a0860100000000000000\x04TEST\nToken name\x10https://test.com\x05notes'
```

**Metadata**

Metadata are usefull to add specific token informations or to diferenciate NFT collections. It is also generally represented as a JSON structure (115 chars):

```json
{"name":"arky logo","type":"image/png","url":"ipfs://bafkreigfxalrf52xm5ecn4lorfhiocw4x5cxpktnkiq3atq6jp2elktobq"}
```

But it uses even less space when serialized (101 chars):

```python
'\x04name\tarky logo\x04type\timage/png\x03urlBipfs://bafkreigfxalrf52xm5ecn4lorfhiocw4x5cxpktnkiq3atq6jp2elktobq'
```

## Journal

Database containing the deserialized smartbridge history. It stores contract inputs and timestamp execution (ie block transaction timestamp) with `nok` set to `False` if success or `True` on failure. All SLP database can be rebuilt from this database.

timestamp|nok|tx|tb|id|de|qt|sy|na|du|no|pa|mi|ch|dt|wt|pk
-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-

**Journal state**

Even if SQL allow fast computation on stored data, it is interesting to compute a database state on node start and increment it on each contract execution.

_Supply state_:
tokenId|owner|free|circulating|paused
-|-|-|-|-
-|-|-|-|-

_User state_:
address|tokenId|balance|frozen|authmeta
-|-|-|-|-
-|-|-|-|-

## Token

Term|Definition
-|-
global supply|maximum allowed token for a contract
free token|undistributed token (on `OWNER` wallet)
minted token|token added to free supply (added to `OWNER` wallet)
burned token|token removed from free supply (removed from  `OWNER` wallet)
circulating token|token from all wallets except `OWNER`
offchain token|cross exchanged token
onchain token|free token + circulating token - burned token - offchain token

**Accounting**

timestamp|tx|tokenId|nok|tp|de|sy|na|du|qt|no|pa|mi
-|-|-|-|-|-|-|-|-|-|-|-|-
1638264520|_txId_|||GENESIS|2|TTK|Test Token||150000||True|True
1638265720|_txId_|aabe4d0aee||MINT|||||85.00
**1638265815**|**_txId_**|**aabe4d0aee**||**SEND**|||||**10.50**
1638265973|_txId_|aabe4d0aee||BURN|||||27.00
1638266083|_txId_|aabe4d0aee||CCXO|||||20.00|_altBlockchainAddress_
1638267582|_altTxId_|aabe4d0aee||CCXI|||||9.5|_DJDypG6SVf_
**1638267817**|**_txId_**|**aabe4d0aee**||**SEND**|||||**9.5**

timestamp|tokenId|address|exchanged|crossed|minted|burned
-|-|-|-|-|-|-
1638265720|aabe4d0aee|DCytPA7wnA|||85.00
**1638265815**|**aabe4d0aee**|**DCytPA7wnA**|**-10.50**
**1638265815**|**aabe4d0aee**|**DMzBk9WdM3**|**10.50**
1638265973|aabe4d0aee|DCytPA7wnA||||-27.00
1638266083|aabe4d0aee|DCytPA7wnA||-20.00
1638267582|aabe4d0aee|DJDyG6SVf||9.50
**1638267817**|**aabe4d0aee**|**DJDyG6SVf**|**-9.50**
**1638267817**|**aabe4d0aee**|**DCytPA7wnA**|**9,50**

**SQL glimpse**

_Free token_:

```SQL
SELECT SUM(exchanged, crossed, minted, burned) FROM accountings
WHERE address IN (
    SELECT address FROM owners WHERE tokenId='aabe4d0aee'
) AND tokenId='aabe4d0aee';
```
_Circulating token_:
```SQL
SELECT SUM(exchanged, crossed) FROM accountings
WHERE address NOT IN (
    SELECT address FROM owners WHERE tokenId='aabe4d0aee'
) AND tokenId='aabe4d0aee';
```
_Available token_:
```SQL
SELECT SUM(minted, burned, crossed) FROM accountings
WHERE tokenId='aabe4d0aee';
```
_Balances_:
```SQL
SELECT address, SUM(exchanged, crossed, minted, burned) FROM accountings
WHERE tokenId='aabe4d0aee';
```

<!-- # Journal

Let's consider events below:

  - `DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA` creates and owns contract `aabe476e47b1cc79e7868ddbce0d0aee`
  - `DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA` mints `85` token
  - `DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA` sends `10.5` token to `DMzBk3g7ThVQPYmpYDTHBHiqYuTtZ9WdM3`
  - `DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA` burns `27` token
  - `DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA` cross exchanges `20` token with another SLP blockchain
  - another SLP blockchain cross exchanges back `9.5` token to `DJDypKeHGeLHNdHdDThsgVQhFHicUG6SVf`
  - `DJDypKeHGeLHNdHdDThsgVQhFHicUG6SVf` sends `9.5` token to `DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA`

**Records**

timestamp|tx|tokenId|nok|tp|de|sy|na|du|qt|no|pa|mi
-|-|-|-|-|-|-|-|-|-|-|-|-
1638264520|_blockchainTxId_|||GENESIS|2|TTK|Test Token||150000||True|True
1638265720|_blockchainTxId_|aabe476e47b1cc79e7868ddbce0d0aee||MINT|||||85.00
**1638265815**|**blockchainTxId**|**aabe476e47b1cc79e7868ddbce0d0aee**||**SEND**|||||**10.50**
1638265973|_blockchainTxId_|aabe476e47b1cc79e7868ddbce0d0aee||BURN|||||27.00
1638266083|_blockchainTxId_|aabe476e47b1cc79e7868ddbce0d0aee||CCXO|||||20.00|_altBlockchainAddress_
1638267582|_alt_BlockchainTxId_|aabe476e47b1cc79e7868ddbce0d0aee||CCXI|||||9.5|_DJDypKeHGeLHNdHdDThsgVQhFHicUG6SVf_
**1638267817**|**blockchainTxId**|**aabe476e47b1cc79e7868ddbce0d0aee**||**SEND**|||||**9.5**

**Contract**:

Unique and immutable line per contract.

timestamp|tokenId|type|name|symbol|globalSupply|decimals|notes|uri|pausable|mintable
-|-|-|-|-|-|-|-|-|-|-
1638264520|aabe476e47b1cc79e7868ddbce0d0aee|slp1|Test token|TTK|150000|2|||True|True

**Owners**

timestamp|tokenId|type|address
-|-|-|-
1638264520|aabe476e47b1cc79e7868ddbce0d0aee|slp1|DCytPd4qzrMTVCz1q3398yA9Md1SuA7wnA

**Metadata**

timestamp|tokenId|address|data
-|-|-|-

**Accountings**

timestamp|tokenId|address|exchanged|crossed|minted|burned
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
tokenId|owner|free|circulating|paused
-|-|-|-|-

**User state**:
address|tokenId|balance|frozen|authmeta
-|-|-|-|-

## SQL glimpse

**Free token**:
```SQL
SELECT SUM(exchanged, crossed, minted, burned) FROM accountings
WHERE address IN (
    SELECT address FROM owners WHERE tokenId='aabe476e47b1cc79e7868ddbce0d0aee'
) AND tokenId='aabe476e47b1cc79e7868ddbce0d0aee';
```
**Circulating token**:
```SQL
SELECT SUM(exchanged, crossed) FROM accountings
WHERE address NOT IN (
    SELECT address FROM owners WHERE tokenId='aabe476e47b1cc79e7868ddbce0d0aee'
) AND tokenId='aabe476e47b1cc79e7868ddbce0d0aee';
```
**Available token**:
```SQL
SELECT SUM(minted, burned, crossed) FROM accountings
WHERE tokenId='aabe476e47b1cc79e7868ddbce0d0aee';
```
**Balances**:
```SQL
SELECT address, SUM(exchanged, crossed, minted, burned) FROM accountings
WHERE tokenId='aabe476e47b1cc79e7868ddbce0d0aee';
``` -->

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
  3. validators answer `True` if accepted or `False` if refused with the asked height supply state hash: `sha256(tokenId|owner|free|circulating|paused)`
  4. if corrum reached, return orphan transaction with SLP smartbridge

on receiving webhook data `transaction.applied`:
  1. deserialize smartbridge and check if it matches locally
  2. add deserialized smartbridge into record database with `nok=True` if error 
  3. apply the contract if `nok==False`
