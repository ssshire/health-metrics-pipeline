with source as (
    select * from {{ source('raw', 'places_county') }}
),

renamed as (
    select
        "StateAbbr"         as state_abbr,
        "StateDesc"         as state_name,
        "CountyName"        as county_name,
        "CountyFIPS"        as county_fips,
        "Category"          as category,
        "Measure"           as measure,
        "Data_Value"::numeric as data_value,
        "Data_Value_Unit"   as data_value_unit,
        "Low_Confidence_Limit"::numeric  as low_confidence_limit,
        "High_Confidence_Limit"::numeric as high_confidence_limit,
        "TotalPopulation"::integer       as total_population,
        "Year"::integer                  as year
    from source
    where "Data_Value" is not null
)

select * from renamed