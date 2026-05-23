class TurtleSignal {
  final String symbol;
  final String assetType;
  final int system;
  final String signal;
  final double price;
  final double atr;
  final double stopLoss;
  final dynamic unitSize;
  final List<double> pyramidTargets;
  final String generatedAt;

  TurtleSignal({
    required this.symbol,
    required this.assetType,
    required this.system,
    required this.signal,
    required this.price,
    required this.atr,
    required this.stopLoss,
    required this.unitSize,
    required this.pyramidTargets,
    required this.generatedAt,
  });

  factory TurtleSignal.fromJson(Map<String, dynamic> j) => TurtleSignal(
        symbol: j['symbol'],
        assetType: j['asset_type'],
        system: j['system'],
        signal: j['signal'],
        price: (j['price'] as num).toDouble(),
        atr: (j['atr'] as num).toDouble(),
        stopLoss: (j['stop_loss'] as num).toDouble(),
        unitSize: j['unit_size'],
        pyramidTargets: (j['pyramid_targets'] as List)
            .map((e) => (e as num).toDouble())
            .toList(),
        generatedAt: j['generated_at'] ?? '',
      );

  bool get isEntry => signal.startsWith('entry');
  bool get isLong => signal.contains('long');

  String get signalLabel {
    switch (signal) {
      case 'entry_long': return '매수 진입';
      case 'entry_short': return '매도 진입';
      case 'exit_long': return '매수 청산';
      case 'exit_short': return '매도 청산';
      default: return signal;
    }
  }

  String get assetLabel {
    switch (assetType) {
      case 'domestic': return '국내주식';
      case 'overseas': return '해외주식';
      case 'crypto': return '가상자산';
      default: return assetType;
    }
  }
}


class WatchlistItem {
  final String symbol;
  final String name;
  final String assetType;
  final double price;
  final double s1High;
  final double s2High;
  final double atr;
  final bool hasSignal;

  WatchlistItem({
    required this.symbol,
    required this.name,
    required this.assetType,
    required this.price,
    required this.s1High,
    required this.s2High,
    required this.atr,
    required this.hasSignal,
  });

  double get s1DistancePct => s1High > 0 ? (s1High - price) / price * 100 : 0;
  double get s2DistancePct => s2High > 0 ? (s2High - price) / price * 100 : 0;
}
