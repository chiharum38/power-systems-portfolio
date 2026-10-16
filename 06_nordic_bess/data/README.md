# Data

The model reads one merged hourly CSV with these columns:

| column | unit | source |
| --- | --- | --- |
| `timestamp` | ISO 8601, Europe/Stockholm | all |
| `da_eur_mwh` | EUR/MWh | ENTSO-E Transparency Platform, day-ahead prices, bidding zone SE3 |
| `fcr_d_eur_mw_h` | EUR/MW/h | Svenska kraftnät, FCR-D capacity auction results |
| `fcr_n_eur_mw_h` | EUR/MW/h | Svenska kraftnät, FCR-N capacity auction results |

Notes for building the file:
- Day-ahead prices moved to 15-minute resolution in the EU day-ahead market. Average the four quarter-hours to get hourly values, or the model will misread the day length.
- FCR prices are per MW per hour. Check whether the source reports per block (for example, 4-hour blocks) and convert to hourly.
- Keep the download date and the source URL in a notes file next to the CSV.
- Raw data files are not committed to any repo. Keep only the derived CSV here.
