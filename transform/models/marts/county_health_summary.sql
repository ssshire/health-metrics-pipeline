with base as (
    select * from {{ ref('stg_places_county') }}
)

select
    state_abbr,
    state_name,
    county_name,
    county_fips,
    year,
    category,
    measure,
    data_value,
    data_value_unit,
    low_confidence_limit,
    high_confidence_limit,
    total_population
from base
order by state_abbr, county_name, category, measure