
## API Integration

The project uses ShopWare's public API for data extraction. Documentation can be found at:
[ShopWare API Documentation](https://shop-ware.stoplight.io/docs/public-api)

## Report Details

### Daily Reports Include:
- Appointment forecasts (next 7 weekdays)
- Closed sales summary with:
  - Total revenue
  - Parts and tires costs
  - Margin calculations
  - Car count
  - Average RO value
  - Labor efficiency
- Daily payments received
- Technician billable hours
- Low margin services (< 40%)

### Weekly Reports Include:
- Extended appointment forecasts (next 2 weeks)
- Historical trends visualization for:
  - Revenue
  - Car count
  - Average RO values
  - Parts margin percentages
  - Tires margin percentages
  - Technician billable hours

## Data Flow

1. **Scheduler Trigger**
   ```mermaid
   sequenceDiagram
       Scheduler->>API: Request Data
       API->>ShopWare: API Calls
       ShopWare->>API: Response Data
       API->>Report Generator: Process Data
       Report Generator->>Email Service: HTML Report
       Email Service->>Recipients: Send Email
   ```

2. **Report Generation**
   ```mermaid
   sequenceDiagram
       Report Generator->>Data Collector: Fetch Required Data
       Data Collector->>Data Processor: Raw Data
       Data Processor->>Visualizer: Processed Data
       Visualizer->>HTML Generator: Plots & Tables
       HTML Generator->>Email Service: Final Report
   ```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)

## Author

[concaption](https://github.com/concaption)