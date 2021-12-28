**Side Ledger Protocol**

  <!-- > This is a reflexion about network concensus around Side Ledger Protocol developped on Qredit blockchain. Purpose here is to evaluate the actions that have to be done so SLP networt could act as a side-blockchain. The porpose of this documentation is to maximize abstraction level of SLP so it can run with any blockchain where smartbridge or equivalent can be embeded in a transaction. -->

# Run python-slp node

First [install Mongo DB](https://docs.mongodb.com/manual/tutorial/#installation) and run the mongodb service:

```sh
sudo systemctl start mongod.service
```

Install `python-slp` node via easy installation script:

```sh
bash <(curl -s https://raw.githubusercontent.com/Moustikitos/python-slp/master/slp-install.sh)
```

Then deploy node from python virtual environement:

```sh
. ~/.local/share/slp/venv/bin/activate
cd ~/python-slp
python -c "import app;app.deploy(host='0.0.0.0', port=5100)"
```

`python-slp` node will the run as a background service on your system. Status and logs are accessible from `systemctl` and `journalctl` commands.

`python-slp` can also be launched on server startup:

```sh
sudo systemctl enable slp.service
```

## API endpoint for slp database

An endpoint is available to get data from mongo database with the pattern:

`/<table_name>/find?[field=value&..][&orderBy=field1:direction1,field2:direction2,..][&page=number]`

table name|searchable fields
-|-
slp1|`address`, `tokenId`, `blockStamp`, `owner`, `frozen`
slp2|`address`, `tokenId`, `blockStamp`, `owner`, `frozen`
journal|`slp_type`, `emitter`, `receiver`, `legit`, `tp`, `sy`, `id`, `pa`, `mi`
contracts|`tokenId`, `height`, `index`, `type`, `owner`, `paused`
rejected|`tokenId`, `height`, `index`, `type`, `owner`, `paused`

```bash
curl http://127.0.0.1:5001/slp2/find?tokenId=0c1b5ed5cff799a0dee2cadc6d02ac60
```
```json
{
  "status": 200,
  "meta": {"page": 1, "limit": 100, "totalCount": 2},
  "data": [
    {
      "address": "ARypXg91KdTCFxUCtjktZMdDEne3AcA8A7",
      "tokenId": "0c1b5ed5cff799a0dee2cadc6d02ac60",
      "blockStamp": "17902732#1",
      "owner": false,
      "metadata": {"trait_background": "ice", "trait_base": "zombie", "trait_clothing": "astronaut", "trait_face": "angry", "trait_hat": "beanie"}
    },
    {
      "address": "AR2xF13MYMnTKGiqF5Z6oNp1nMue9Qpp84",
      "tokenId": "0c1b5ed5cff799a0dee2cadc6d02ac60",
      "blockStamp": "17902732#1",
      "owner": true,
      "metadata": {}
    }
  ]
}
```

<!-- # Definitions and rationales

## Smartbridge

Serialized information stored on `vendorField` of all ARK blockchain based transaction. `vendorFIeld` was the very first way ARK considered interoperability with other blockchain before the ARK logic concept. Because of `vendorField` size limitation, contract have to be normalized and serialized so maximum information can be broadcasted within one and single transaction.

## Contract

Provides functions including the transfer of tokens from one account to another, getting the current token balance of an account and getting the total supply of the token available on the network.

timestamp|tokenId|type|name|symbol|globalSupply|decimals|notes|uri|pausable|mintable
-|-|-|-|-|-|-|-|-|-|-
1638264520|aabe476e47b1cc79e7868ddbce0d0aee|slp1|Test token|TTK|150000|2|||True|True

## Contract fields

An input inside a contract is described with one action type and parameters. Because smartbridge size is limited (256 chars), type action and parameters names have to be reduced:

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

More advanced way to represent such data is serialization (80 chars):

```python
'slp1://0008a0860100000000000000\x04TEST\nToken name\x10https://test.com\x05notes'
```

Metadata are usefull to add specific token informations or to diferenciate NFT collection items. It is also generally represented as a JSON structure (115 chars):

```json
{"name":"arky logo","type":"image/png","url":"ipfs://bafkreigfxalrf52xm5ecn4lorfhiocw4x5cxpktnkiq3atq6jp2elktobq"}
```

It uses even less space when serialized (101 chars):

```python
'\x04name\tarky logo\x04type\timage/png\x03urlBipfs://bafkreigfxalrf52xm5ecn4lorfhiocw4x5cxpktnkiq3atq6jp2elktobq'
```

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

Gold rule:

  > **free token + circulating token + burned token + offchain token == minted token <= global supply**

## Journal

Database containing the deserialized smartbridge history. It stores contract inputs and timestamp execution (ie block transaction timestamp) with `apply` set to `True` if success or `False` on failure. All SLP database can be rebuilt from this database.

Let's consider the events:

  - `DCytPA7wnA` creates and owns contract `aabe4d0aee`
  - `DCytPA7wnA` mints `85` token
  - `DCytPA7wnA` sends `10.5` token to `DMzBk9WdM3`
  - `DCytPA7wnA` burns `27` token
  - `DCytPA7wnA` cross exchanges `20` token with another SLP blockchain
  - another SLP blockchain cross exchanges back `9.5` token to `DJDyG6SVf`
  - `DJDyG6SVf` sends `9.5` token to `DCytPA7wnA`

Bellow the proposed way to store inputs:

timestamp|blockheight|txindex|apply|txid|type|tp|id|de|qt|sy|na|du|no|pa|mi|ch|dt|wt|pk
-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
1638264520|250|1||_txId1_|slp1|GENESIS||2|150000|TTK|Test Token|||True|True
1638265720|251|1||_txId2_|slp1|MINT|aabe4d0aee||85.00
**1638265815**|252|1||**_txId3_**|slp1|**SEND**|**aabe4d0aee**||**10.50**
1638265973|253|1||_txId4_|slp1|BURN|aabe4d0aee||27.00
1638266083|254|1||_txId5_|slp1|CCXO|aabe4d0aee||20.00|||||||||_altBlockchainAddress_
1638267582|255|1||_altTxId1_|slp1|CCSI|aabe4d0aee||9.5|||||||||_DJDypG6SVf_
**1638267817**|256|1||**_txId6_**|slp1|**SEND**|**aabe4d0aee**||**9.5**

 - `timestamp`: UTC block timestamp as UNIX representation
 - `blockheight`: the blockchain height
 - `txindex`: rank of the transaction in the block
 - `nok`: valid contract marker (`False` if contract not appliable)
 - `txid`: blockchain transaction id

**Accounting**

A token can be minted, exchanged, cross exchanged or burned. In order to follow the token distribution within contracts, an accounting database have to be updated. Bellow the way it should be populated according to inputs from above.

height|timestamp|tokenId|address|exchanged|crossed|minted|burned
-|-|-|-|-|-|-|-
251|1638265720|aabe4d0aee|DCytPA7wnA|||85.00
**252**|**1638265815**|**aabe4d0aee**|**DCytPA7wnA**|**-10.50**
**252**|**1638265815**|**aabe4d0aee**|**DMzBk9WdM3**|**10.50**
253|1638265973|aabe4d0aee|DCytPA7wnA||||-27.00
254|1638266083|aabe4d0aee|DCytPA7wnA||-20.00
255|1638267582|aabe4d0aee|DJDyG6SVf||9.50
**256**|**1638267817**|**aabe4d0aee**|**DJDyG6SVf**|**-9.50**
**256**|**1638267817**|**aabe4d0aee**|**DCytPA7wnA**|**9,50**

With this data description, token distribution can be computed with simple SQL requests:
  * Free token:
```SQL
SELECT SUM(exchanged, crossed, minted, burned) FROM accountings
WHERE address IN (
    SELECT address FROM owners WHERE tokenId='aabe4d0aee'
) AND tokenId='aabe4d0aee';
```
  * Circulating token:
```SQL
SELECT SUM(exchanged, crossed) FROM accountings
WHERE address NOT IN (
    SELECT address FROM owners WHERE tokenId='aabe4d0aee'
) AND tokenId='aabe4d0aee';
```
  * Available token:
```SQL
SELECT SUM(minted, burned, crossed) FROM accountings
WHERE tokenId='aabe4d0aee';
```
  * Balances:
```SQL
SELECT address, SUM(exchanged, crossed, minted, burned) FROM accountings
WHERE tokenId='aabe4d0aee';
```

Even if SQL allow fast computation on stored data, it is interesting to compute a database state on node start and increment it on each contract execution.

  * Supply state

height|tokenId|owner|free|circulating|paused
-|-|-|-|-|-
-|-|-|-|-|-

  * User state

height|address|tokenId|exchanged|crossed|minted|burned|frozen|authmeta|Owner
-|-|-|-|-|-|-|-|-|-
-|-|-|-|-|-|-|-|-|-

# Node concensus

## Relays and validators?

One can consider two types of nodes in SLP ecosystem
  1. validators: nodes runing on a blockchain peer ie with blockchain database access
  2. relays: stand alone running nodes

## SLP contract validation

2 steps are needed to validate an SLP contract:
  - on contract proposition: 
    + wallet issuing the contract is not known yet and have to be mentioned in the proposition request header as `Wallet-address` value
    * need concensus to validate contract proposition
    * return an orphan transaction with SLP contract as `vendorField`
  - on finalized transaction reception:
    + wallet issuing the contract is known
    * no concensus needed
    * broadcast transaction if it matches contract specification

## Concensus

on receiving proposition:
  1. check if it matches locally
  2. broadcast proposition and wallet to known validators with the last known contract height
  3. validators answer `True` with the asked height supply state hash `sha256(height|tokenId|owner|free|circulating|paused)` if accepted or `False` if refused
  4. if corrum reached, return orphan transaction with SLP smartbridge

on concensus request:
  1. check if asked height <= local height
  2. compute back supply state to asked height if needed
  3. check if proposition matches locally
  4. return `True` with `sha256(height|tokenId|owner|free|circulating|paused)` if proposition matches else `False`

on receiving `transaction.applied` webhook data :
  1. deserialize smartbridge and check if it matches locally
  2. add deserialized smartbridge into record database with `nok=True` if error 
  3. apply the contract if `nok==False` -->
