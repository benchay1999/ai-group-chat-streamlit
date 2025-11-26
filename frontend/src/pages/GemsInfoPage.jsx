/**
 * Gems Information Page
 * Comprehensive guide to the gem economy system
 */

import { Link } from 'react-router-dom';
import { ArrowLeft, Coins, Users, Trophy, TrendingUp, AlertCircle, DollarSign, Award, Zap, Sparkles } from 'lucide-react';

const GemsInfoPage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-black">
      {/* Header */}
      <div className="bg-white bg-opacity-10 backdrop-blur-md border-b border-white border-opacity-20">
        <div className="max-w-5xl mx-auto px-6 py-6">
          <Link
            to="/dashboard"
            className="inline-flex items-center text-white hover:text-cyan-300 mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Link>
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-2xl flex items-center justify-center shadow-lg">
              <Coins className="w-10 h-10 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-white">💎 Gem System Guide</h1>
              <p className="text-cyan-300 mt-1">Everything you need to know about earning gems</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-6 py-12">
        
        {/* Overview Card */}
        <div className="bg-gradient-to-br from-purple-600 to-blue-600 rounded-2xl p-8 text-white mb-8 shadow-2xl">
          <div className="flex items-start gap-4">
            <Coins className="w-12 h-12 flex-shrink-0" />
            <div>
              <h2 className="text-3xl font-bold mb-3">What are Gems?</h2>
              <p className="text-lg opacity-95 leading-relaxed">
                Gems are the in-game currency you earn by playing games. They can be converted to real USD 
                via Amazon Mechanical Turk cashouts. <strong>1,000 gems = $1.00 USD</strong>
              </p>
            </div>
          </div>
        </div>

        {/* Single-Human Games */}
        <div className="bg-gray-800 bg-opacity-50 backdrop-blur-sm rounded-xl p-8 mb-8 border border-gray-700">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 bg-green-500 rounded-xl flex items-center justify-center">
              <Users className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-white">Single-Player Games</h2>
          </div>

          <div className="space-y-4 text-gray-300">
            <p className="text-lg">
              1 human player vs AI agents. Simple participation rewards.
            </p>

            <div className="bg-gray-900 bg-opacity-50 rounded-lg p-6 border-l-4 border-green-500">
              <h3 className="text-xl font-bold text-white mb-3">💰 Rewards</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-gray-300">Everyone (human + AI):</span>
                  <span className="text-green-400 font-bold text-lg">+50 gems</span>
                </div>
              </div>
              <p className="text-sm text-gray-400 mt-4">
                ✅ No stakes required<br />
                ✅ No risk of losing gems<br />
                ✅ Pure participation reward
              </p>
            </div>
          </div>
        </div>

        {/* Multi-Human Games */}
        <div className="bg-gray-800 bg-opacity-50 backdrop-blur-sm rounded-xl p-8 mb-8 border border-gray-700">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 bg-orange-500 rounded-xl flex items-center justify-center">
              <Trophy className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-white">Multi-Player Games</h2>
          </div>

          <div className="space-y-6 text-gray-300">
            <p className="text-lg">
              2+ human players competing. Strategic voting with stakes system.
            </p>

            {/* Stakes Requirement */}
            <div className="bg-red-900 bg-opacity-30 rounded-lg p-6 border-l-4 border-red-500">
              <div className="flex items-center gap-2 mb-3">
                <AlertCircle className="w-5 h-5 text-red-400" />
                <h3 className="text-xl font-bold text-white">⚠️ Stakes Required</h3>
              </div>
              <p className="text-gray-300 mb-3">
                To join multi-player games, you need <strong className="text-white">minimum 250 gems</strong>.
              </p>
              <p className="text-sm text-gray-400">
                Stakes are calculated as a percentage of your balance (10%, 30%, 50%, or 100%). 
                All players risk the <strong>minimum stake</strong> (lowest among all players).
              </p>
            </div>

            {/* Phase 1: Deduction */}
            <div className="bg-gray-900 bg-opacity-50 rounded-lg p-6">
              <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-400" />
                Phase 1: Game Start (Deduction)
              </h3>
              <div className="space-y-3 text-sm">
                <p>When the game starts:</p>
                <ol className="list-decimal list-inside space-y-2 ml-2">
                  <li>System calculates each player's stake (balance × percentage)</li>
                  <li>Finds the <strong className="text-cyan-400">minimum stake</strong> across all players</li>
                  <li><strong className="text-red-400">Deducts</strong> minimum stake from ALL players immediately</li>
                  <li>Creates stake record in database</li>
                </ol>
                
                <div className="bg-gray-800 rounded p-3 mt-4 font-mono text-xs">
                  <div className="text-gray-400 mb-2">Example (3 players, 10% stake):</div>
                  <div className="text-green-400">Player A: 1000 gems × 10% = 100 stake</div>
                  <div className="text-green-400">Player B: 900 gems × 10% = 90 stake</div>
                  <div className="text-green-400">Player C: 800 gems × 10% = 80 stake</div>
                  <div className="text-yellow-400 mt-2">minimum_stake = 80 gems</div>
                  <div className="text-red-400 mt-2">All players lose 80 gems immediately</div>
                </div>
              </div>
            </div>

            {/* Phase 2: Game End */}
            <div className="bg-gray-900 bg-opacity-50 rounded-lg p-6">
              <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Trophy className="w-5 h-5 text-yellow-400" />
                Phase 2: Game End (Rewards)
              </h3>
              
              {/* Base Gems */}
              <div className="mb-6">
                <h4 className="font-bold text-white mb-2">📦 Base Gems (Everyone)</h4>
                <div className="bg-green-900 bg-opacity-30 rounded p-4 border-l-4 border-green-500">
                  <div className="flex items-center justify-between">
                    <span>All participants:</span>
                    <span className="text-green-400 font-bold text-lg">+100 gems</span>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">Guaranteed participation reward</p>
                </div>
              </div>

              {/* Stakes Distribution */}
              <div>
                <h4 className="font-bold text-white mb-3">🎯 Stakes Distribution</h4>
                
                {/* Winners */}
                <div className="bg-blue-900 bg-opacity-30 rounded p-4 border-l-4 border-blue-500 mb-4">
                  <h5 className="font-bold text-blue-300 mb-3">🏆 Winners (Most Votes)</h5>
                  <ol className="list-decimal list-inside space-y-2 text-sm">
                    <li><strong className="text-green-400">Stake refund</strong>: Get your stake back (guaranteed)</li>
                    <li><strong className="text-cyan-400">Loser pool</strong>: All loser stakes combined</li>
                    <li><strong className="text-yellow-400">Equal division</strong>: Pool ÷ number of winners</li>
                    <li><strong className="text-purple-400">Accuracy bonus</strong>: You get (accuracy% × your share)</li>
                  </ol>
                  
                  <div className="bg-gray-800 rounded p-3 mt-4 font-mono text-xs">
                    <div className="text-cyan-400">stake_refund = minimum_stake (always returned)</div>
                    <div className="text-yellow-400">loser_pool = minimum_stake × num_losers</div>
                    <div className="text-green-400">your_share = loser_pool ÷ num_winners</div>
                    <div className="text-purple-400">accuracy = correct_votes ÷ (num_humans - 1)</div>
                    <div className="text-white mt-2">stake_winnings = accuracy × your_share</div>
                    <div className="text-green-400 font-bold mt-2">TOTAL = refund + winnings</div>
                  </div>
                </div>

                {/* Losers */}
                <div className="bg-red-900 bg-opacity-30 rounded p-4 border-l-4 border-red-500">
                  <h5 className="font-bold text-red-300 mb-2">💔 Losers (Fewer Votes)</h5>
                  <div className="text-sm space-y-2">
                    <div className="flex items-center justify-between">
                      <span>Stakes returned:</span>
                      <span className="text-red-400 font-bold">0 gems</span>
                    </div>
                    <p className="text-gray-400 text-xs mt-2">
                      Losers forfeit their stakes entirely. These go to the winner pool.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Example Scenario */}
            <div className="bg-gradient-to-br from-purple-900 to-blue-900 rounded-lg p-6 border border-purple-500">
              <h3 className="text-2xl font-bold text-white mb-4">📊 Example: 2 Players</h3>
              
              <div className="space-y-4 text-sm">
                <div className="bg-black bg-opacity-30 rounded p-4">
                  <div className="text-yellow-400 font-bold mb-2">Game Start:</div>
                  <div className="space-y-1 text-gray-300">
                    <div>Player A: 1000 gems → 840 gems (-160 deducted)</div>
                    <div>Player B: 1000 gems → 840 gems (-160 deducted)</div>
                  </div>
                </div>

                <div className="bg-black bg-opacity-30 rounded p-4">
                  <div className="text-cyan-400 font-bold mb-2">Voting Results:</div>
                  <div className="space-y-1 text-gray-300">
                    <div>Player A: 1 vote ← Winner 🏆</div>
                    <div>Player B: 0 votes</div>
                  </div>
                </div>

                <div className="bg-black bg-opacity-30 rounded p-4">
                  <div className="text-green-400 font-bold mb-3">Rewards:</div>
                  
                  <div className="mb-4 pb-4 border-b border-gray-700">
                    <div className="text-white font-semibold mb-2">Player A (Winner):</div>
                    <div className="space-y-1 pl-4">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Base:</span>
                        <span className="text-green-400">+100 gems</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Stake refund:</span>
                        <span className="text-green-400">+160 gems</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Stakes won (100%):</span>
                        <span className="text-green-400">+160 gems</span>
                      </div>
                      <div className="flex justify-between font-bold pt-2 border-t border-gray-600">
                        <span className="text-white">Total credited:</span>
                        <span className="text-green-400">+420 gems</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="text-white font-semibold mb-2">Player B (Loser):</div>
                    <div className="space-y-1 pl-4">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Base:</span>
                        <span className="text-green-400">+100 gems</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Stakes returned:</span>
                        <span className="text-red-400">0 gems</span>
                      </div>
                      <div className="flex justify-between font-bold pt-2 border-t border-gray-600">
                        <span className="text-white">Total credited:</span>
                        <span className="text-yellow-400">+100 gems</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-black bg-opacity-30 rounded p-4">
                  <div className="text-purple-400 font-bold mb-2">Final Balances:</div>
                  <div className="space-y-1 text-gray-300">
                    <div className="flex justify-between">
                      <span>Player A:</span>
                      <span className="text-green-400 font-bold">1260 gems (+260 net 🎉)</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Player B:</span>
                      <span className="text-red-400 font-bold">940 gems (-60 net 💔)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Key Formulas */}
            <div className="bg-gray-900 bg-opacity-50 rounded-lg p-6 border border-cyan-500">
              <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                <Award className="w-6 h-6 text-cyan-400" />
                Key Formulas
              </h3>
              
              <div className="space-y-4 font-mono text-sm">
                <div className="bg-gray-800 rounded p-4">
                  <div className="text-cyan-400 font-bold mb-2">For Winners:</div>
                  <div className="space-y-1 text-gray-300">
                    <div className="text-gray-400">// 1. Pool from losers</div>
                    <div>loser_pool = minimum_stake × num_losers</div>
                    <div>max_share = loser_pool ÷ num_winners</div>
                    
                    <div className="mt-3 text-gray-400">// 2. Calculate voting accuracy</div>
                    <div>votes_needed = num_humans - 1</div>
                    <div className="text-gray-500 text-xs">  // Must vote for all OTHER humans</div>
                    <div>correct_votes = count(voted for other humans)</div>
                    <div className="text-gray-500 text-xs">  // Not self, not AI</div>
                    <div className="text-purple-400 mt-1">accuracy = correct_votes / votes_needed</div>
                    <div className="text-gray-500 text-xs">  // Returns decimal: 0.0 to 1.0</div>
                    <div className="text-gray-500 text-xs">  // Example: 2/2 = 1.0 = 100%</div>
                    
                    <div className="mt-3 text-gray-400">// 3. Calculate rewards</div>
                    <div className="text-yellow-400">stake_refund = minimum_stake</div>
                    <div className="text-gray-500 text-xs">  // Always returned ✅</div>
                    <div className="text-green-400 mt-1">stake_winnings = int(accuracy × max_share)</div>
                    <div className="text-gray-500 text-xs">  // Proportional to accuracy</div>
                    <div className="text-white font-bold mt-2 pt-2 border-t border-gray-600">TOTAL = 100 + refund + winnings</div>
                  </div>
                </div>

                <div className="bg-gray-800 rounded p-4">
                  <div className="text-red-400 font-bold mb-2">For Losers:</div>
                  <div className="space-y-1 text-gray-300">
                    <div>stake_refund = 0</div>
                    <div>stake_winnings = 0</div>
                    <div className="text-white font-bold mt-1 pt-1 border-t border-gray-600">TOTAL = 100 + 0 = 100 gems</div>
                    <div className="text-red-400 mt-2">Net change = 100 - minimum_stake</div>
                    <div className="text-gray-500 text-xs">  // Always negative ❌</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Voting Accuracy */}
            <div className="bg-gray-900 bg-opacity-50 rounded-lg p-6">
              <h3 className="text-2xl font-bold text-white mb-4">🎯 Voting Accuracy Matters!</h3>
              <p className="text-gray-300 mb-4">
                In multi-player games, you vote for other human players (not yourself). 
                Your accuracy determines how much of the loser pool you collect.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-green-900 bg-opacity-40 rounded-lg p-4 border border-green-600">
                  <div className="text-2xl font-bold text-green-400 mb-2">100%</div>
                  <div className="text-sm text-gray-300">All votes correct</div>
                  <div className="text-xs text-green-300 mt-2">Get full share of loser pool</div>
                </div>
                
                <div className="bg-yellow-900 bg-opacity-40 rounded-lg p-4 border border-yellow-600">
                  <div className="text-2xl font-bold text-yellow-400 mb-2">50%</div>
                  <div className="text-sm text-gray-300">Half votes correct</div>
                  <div className="text-xs text-yellow-300 mt-2">Get half of your share</div>
                </div>
                
                <div className="bg-red-900 bg-opacity-40 rounded-lg p-4 border border-red-600">
                  <div className="text-2xl font-bold text-red-400 mb-2">0%</div>
                  <div className="text-sm text-gray-300">No correct votes</div>
                  <div className="text-xs text-red-300 mt-2">Only get stake refund</div>
                </div>
              </div>
            </div>

            {/* Guarantees */}
            <div className="bg-gradient-to-br from-green-900 to-emerald-900 rounded-lg p-6 border border-green-500">
              <h3 className="text-2xl font-bold text-white mb-4">✅ Guarantees</h3>
              <div className="space-y-2 text-gray-200">
                <div className="flex items-start gap-2">
                  <span className="text-green-400 font-bold">✓</span>
                  <span><strong>Winners never lose gems</strong> - Minimum: +100 base (even with 0% accuracy)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-400 font-bold">✓</span>
                  <span><strong>Higher accuracy = higher reward</strong> - Up to full share of loser pool</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-400 font-bold">✓</span>
                  <span><strong>Fair competition</strong> - Winners split loser pool equally</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-yellow-400 font-bold">⚠</span>
                  <span><strong>House collects residual</strong> - Uncollected gems (from low accuracy) don't go back to losers</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Cashout Information */}
        <div className="bg-gradient-to-br from-green-600 to-emerald-600 rounded-2xl p-8 text-white shadow-2xl">
          <div className="flex items-start gap-4">
            <DollarSign className="w-12 h-12 flex-shrink-0" />
            <div>
              <h2 className="text-3xl font-bold mb-3">💵 Converting Gems to USD</h2>
              <div className="space-y-3 text-lg opacity-95">
                <p><strong>Conversion Rate:</strong> 1,000 gems = $1.00 USD</p>
                <p><strong>Minimum Cashout:</strong> $5.00 (5,000 gems)</p>
                <p><strong>Method:</strong> Amazon Mechanical Turk</p>
                <p className="text-sm opacity-90 mt-4">
                  Visit the Wallet page to cash out your gems. You'll need to provide your MTurk Worker ID.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Tips */}
        <div className="bg-gray-800 bg-opacity-50 backdrop-blur-sm rounded-xl p-8 mt-8 border border-gray-700">
          <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-cyan-400" />
            Pro Tips
          </h2>
          <ul className="space-y-3 text-gray-300">
            <li className="flex items-start gap-3">
              <span className="text-cyan-400 font-bold text-xl">1.</span>
              <span><strong className="text-white">Start with single-player games</strong> to build your gem balance risk-free</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-cyan-400 font-bold text-xl">2.</span>
              <span><strong className="text-white">Vote strategically</strong> in multi-player games - identify all other humans correctly for maximum rewards</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-cyan-400 font-bold text-xl">3.</span>
              <span><strong className="text-white">Watch your stake percentage</strong> - higher stakes mean more risk but also more potential reward</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-cyan-400 font-bold text-xl">4.</span>
              <span><strong className="text-white">Act human-like</strong> in multi-player games - getting votes means you win!</span>
            </li>
          </ul>
        </div>

        {/* CTA */}
        <div className="text-center mt-12">
          <Link
            to="/lobby"
            className="inline-flex items-center gap-3 px-10 py-5 bg-gradient-to-r from-green-500 via-cyan-500 to-blue-500 text-white rounded-xl font-bold text-xl hover:from-green-600 hover:via-cyan-600 hover:to-blue-600 transition-all transform hover:scale-105 shadow-2xl"
          >
            <Coins className="w-6 h-6" />
            Start Earning Gems
            <Sparkles className="w-6 h-6" />
          </Link>
          <p className="text-gray-400 mt-4">
            Ready to put your skills to the test?
          </p>
        </div>
      </div>
    </div>
  );
};

export default GemsInfoPage;

