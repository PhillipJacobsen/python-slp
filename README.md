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

Then deploy node from python virtual environement:

```sh
. ~/.local/share/slp/venv/bin/activate
cd ~/python-slp
python -c "import app;app.deploy(host='0.0.0.0', port=5100, blockchain='ark')"
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
contracts|`tokenId`, `height`, `index`, `type`, `owner`, `paused`, `symbol`
rejected|`tokenId`, `height`, `index`, `type`, `owner`, `paused`, `symbol`

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

# Releases

## 0.3.2 - Aquila
  - [x] `ubuntu` install script
  - [x] blockchain syncer
  - [x] full SLP1 contract execution
  - [ ] partial SLP2 contract execution (CLONE missing)
  - [x] mongo db api
