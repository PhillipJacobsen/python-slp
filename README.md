**Side Ledger Protocol**

# Run python-slp node

First [install Mongo DB](https://docs.mongodb.com/manual/tutorial/#installation) and run the mongodb service:

```sh
sudo systemctl start mongod.service
```

Install `python-slp` node via easy installation script:

```sh
bash <(curl -s https://raw.githubusercontent.com/Moustikitos/python-slp/master/slp-install.sh)
```

`python-slp` node will then run as a background service on your system. Status and logs are accessible from `systemctl` and `journalctl` commands.

`python-slp` can also be launched on server startup:

```sh
sudo systemctl enable mongod.service
sudo systemctl enable slp.service
```

## Settings

  * [x] webhook has to be enabled on `Ark` relay
  * [x] set `webhook peer` in `ark.json` file

**if `python-slp` is running on a standalone node**

  * [x] node ip where `python-slp` is installed has to be whitelisted by the `Ark` relay

## Custom deployment

`python-slp` is configured for `Ark` blockchain on port 5200 and 5100. To deploy node and api with a specific `Ark-fork`, copy `ark.json` to `name.json` in package directory where `name` is the name of the targeted blockchain. Then edit created json file accordingly and deploy:

```sh
python -c "import app;app.deploy(host='127.0.0.1', port=5243, blockchain='name')"
python -c "import slp.api;slp.api.deploy(host='127.0.0.1', port=5124, blockchain='name')"
```

Where `name` is the basename of json configuration used to store specific blockchain parameters.

## Webhook management

Webhook subsciption is done on `python-slp` launch. It can also be created/removed with:

```sh
python -c "import app;app.init('ark');app.sync.chain.subscribe()"
python -c "import app;app.init('name');app.sync.chain.unsubscribe()"
```

## API endpoint for slp database

An endpoint is available to get data from mongo database with the pattern:

```
/<table_name>/find[?field=value&..][&operator_field=op:value&..][&orderBy=field_i:direction_i,..][&page=number]
```

Where:
  - op is one of `eq`, `neg`, `gt`, `gte`, `lt`, `lte`
  - direction `desc` or `reversed` (default is `asc`)

table name|fields|operator fields
-|-|-
slp1|`address`, `tokenId`, `blockStamp`, `owner`, `frozen`|`balance`
slp2|`address`, `tokenId`, `blockStamp`, `owner`, `frozen`
journal|`slp_type`, `emitter`, `receiver`, `legit`, `tp`, `sy`, `id`, `pa`, `mi`|`qt`
contracts|`tokenId`, `height`, `index`, `type`, `owner`, `paused`, `symbol`|`minted`, `burned`, `exited`, `globalSupply`
rejected|`tokenId`, `height`, `index`, `type`, `owner`, `paused`, `symbol`|`minted`, `burned`, `exited`, `globalSupply`

```bash
curl http://127.0.0.1:5100/slp2/find?tokenId=0c1b5ed5cff799a0dee2cadc6d02ac60
```
```json
{
  "status": 200,
  "meta": {
    "page": 1,
    "totalPage": 1,
    "count": 2,
    "totalCount": 2
  },
  "data": [
    {
      "address": "ARypXg91KdTCFxUCtjktZMdDEne3AcA8A7",
      "tokenId": "0c1b5ed5cff799a0dee2cadc6d02ac60",
      "blockStamp": "17902732#1",
      "owner": false,
      "metadata": {
        "trait_background": "ice",
        "trait_base": "zombie",
        "trait_clothing": "astronaut",
        "trait_face": "angry",
        "trait_hat": "beanie"
      }
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

# Releases

## current work
  - [x] full SLP2 contract execution
  - [x] SIGTEMR securely handled
  - [x] run slp API separately
  - [ ] TODO:
    - [ ] documentation
    - [ ] use websocket to sync slp database
    - [ ] slp database rebuild before sync process
    - [ ] p2p messaging
    - [ ] improve logging messages

## 0.3.2 - Aquila
  - [x] `ubuntu` install script
  - [x] blockchain syncer
  - [x] full SLP1 contract execution
  - [ ] partial SLP2 contract execution (CLONE missing)
  - [x] mongo db api
