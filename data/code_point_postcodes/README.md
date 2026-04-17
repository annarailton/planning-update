# Code-Point postcode data

This folder contains a local copy of the `ox.csv` postcode centroid file from
Ordnance Survey's **Code-Point Open** dataset.

## Source

- Product page: https://www.ordnancesurvey.co.uk/products/code-point-open
- Documentation: https://docs.os.uk/os-downloads/addressing-and-location/code-point-open
- Licence: Open Government Licence v3.0

Code-Point Open provides postcode unit centroids in **British National Grid**
coordinates. In this repo we use that data to turn a postcode into a point,
then test which checked-in Oxford ward polygon contains it.

The checked-in [ox.csv](/Users/annarailton/projects/planning-update/data/code_point_postcodes/ox.csv)
is the Oxford postcode area CSV from the standard Code-Point Open download.

## File format

Rows look like:

```csv
"OX1 1AA",10,450673,205980,"E92000001","E19000002","E18000009","E10000025","E07000178","E05013111"
```

For the current lookup script, the important columns are:

- column 1: postcode
- column 3: easting
- column 4: northing
