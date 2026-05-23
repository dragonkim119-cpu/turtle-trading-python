import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/signal.dart';
import '../services/api_service.dart';

class SignalsScreen extends StatefulWidget {
  const SignalsScreen({super.key});
  @override
  State<SignalsScreen> createState() => _SignalsScreenState();
}

class _SignalsScreenState extends State<SignalsScreen> {
  List<TurtleSignal> _signals = [];
  bool _loading = false;
  String? _error;
  String _filter = 'all';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final signals = await ApiService.getSignals();
      setState(() { _signals = signals; });
    } catch (e) {
      setState(() { _error = e.toString(); });
    } finally {
      setState(() { _loading = false; });
    }
  }

  Future<void> _scan() async {
    setState(() { _loading = true; _error = null; });
    try {
      final count = await ApiService.triggerScan();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('스캔 완료 — 신호 $count개')),
      );
      await _load();
    } catch (e) {
      setState(() { _error = e.toString(); });
    } finally {
      setState(() { _loading = false; });
    }
  }

  List<TurtleSignal> get _filtered {
    if (_filter == 'all') return _signals;
    return _signals.where((s) => s.assetType == _filter).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('터틀 신호'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: _loading ? null : _scan,
            tooltip: '전종목 스캔',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildFilterBar(),
          if (_loading) const LinearProgressIndicator(),
          if (_error != null) _buildError(),
          Expanded(child: _buildList()),
        ],
      ),
    );
  }

  Widget _buildFilterBar() {
    const filters = [
      ('all', '전체'),
      ('domestic', '국내주식'),
      ('overseas', '해외주식'),
      ('crypto', '가상자산'),
    ];
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: filters.map((f) {
          final selected = _filter == f.$1;
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilterChip(
              label: Text(f.$2),
              selected: selected,
              onSelected: (_) => setState(() => _filter = f.$1),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildError() => Container(
        color: Colors.red[50],
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.red),
            const SizedBox(width: 8),
            Expanded(child: Text(_error!, style: const TextStyle(color: Colors.red))),
          ],
        ),
      );

  Widget _buildList() {
    final items = _filtered;
    if (items.isEmpty && !_loading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.notifications_none, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text('현재 신호 없음', style: TextStyle(color: Colors.grey, fontSize: 16)),
            SizedBox(height: 8),
            Text('상단 검색 버튼으로 스캔', style: TextStyle(color: Colors.grey)),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        itemCount: items.length,
        itemBuilder: (ctx, i) => _SignalCard(signal: items[i]),
      ),
    );
  }
}


class _SignalCard extends StatelessWidget {
  final TurtleSignal signal;
  const _SignalCard({required this.signal});

  @override
  Widget build(BuildContext context) {
    final isEntry = signal.isEntry;
    final isLong = signal.isLong;
    final color = isEntry
        ? (isLong ? Colors.green : Colors.red)
        : Colors.orange;
    final fmt = NumberFormat('#,##0.####');

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    signal.signalLabel,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF4FC3F7),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text('System ${signal.system}',
                      style: const TextStyle(fontSize: 12, color: Colors.black87, fontWeight: FontWeight.w600)),
                ),
                const Spacer(),
                Text(signal.assetLabel,
                    style: TextStyle(color: Colors.grey[600], fontSize: 12)),
              ],
            ),
            const SizedBox(height: 12),
            Text(signal.symbol,
                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            _row('현재가', fmt.format(signal.price)),
            _row('ATR(20)', fmt.format(signal.atr)),
            if (signal.stopLoss > 0) _row('손절가', fmt.format(signal.stopLoss),
                valueColor: Colors.red),
            if (signal.unitSize != 0) _row('권장 수량', '${signal.unitSize}'),
            if (signal.pyramidTargets.isNotEmpty)
              _row('피라미딩 목표',
                  signal.pyramidTargets.map((p) => fmt.format(p)).join(' → ')),
          ],
        ),
      ),
    );
  }

  Widget _row(String label, String value, {Color? valueColor}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 90,
              child: Text(label,
                  style: TextStyle(color: Colors.grey[600], fontSize: 13)),
            ),
            Expanded(
              child: Text(value,
                  softWrap: true,
                  style: TextStyle(
                      fontWeight: FontWeight.w500,
                      color: valueColor,
                      fontSize: 13)),
            ),
          ],
        ),
      );
}
