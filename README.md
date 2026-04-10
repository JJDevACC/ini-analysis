## Example usage of prism_flow_export.py
python prism_flow_export.py `
  --af-attribute-path "\\MASTERPIDVAPP\db-Development-W-WW-Planning\WASTEWATER\FLOW\LIFTSTATION\HOURLY|WESTERN WY - 8617B" `
  --station-id "WES8617B" `
  --start "2024-06-12T00:00:00Z" `
  --end "2024-09-10T00:00:00Z" `
  --interval "1h" `
  --input-unit "gpm" `
  --output-unit "MGD" `
  --out "WES8617B_test_01.csv"

python prism_flow_export.py --af-attribute-path "\\MASTERPIDVAPP\db-Development-W-WW-Planning\WASTEWATER\FLOW\LIFTSTATION\HOURLY|WESTERN WY - 8617B" --station-id "WES8617B" --start "2024-06-12T00:00:00Z" --end "2024-09-10T00:00:00Z" --interval "1h" --input-unit "gpm" --output-unit "MGD" --out "WES8617B_test_01.csv"

python prism_flow_export.py --af-attribute-path "\\MASTERPIDVAPP\db-Development-W-WW-Planning\WASTEWATER\FLOW\LIFTSTATION\HOURLY|WESTERN WY - 8617B" --station-id "WES8617B" --start "2024-06-12T00:00:00Z" --end "2024-09-10T00:00:00Z" --method average --avg-basis TimeWeighted --avg-timestamp start --input-unit "gpm" --output-unit "MGD" --out "WES8617B_avg_hourly_test_01.csv"
