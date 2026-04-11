import React from 'react';
import { Card, CardContent } from '../components/Card';
import { TrendsIcon } from '../components/Icons';

export const TrendsPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#F6F7F9] pb-20">
      {/* Header */}
      <header className="bg-white px-4 py-6 border-b border-[#E5E7EB]">
        <h1 className="text-2xl font-bold text-[#1A1D21]">Trends</h1>
        <p className="text-sm text-[#8A8E97] mt-0.5">
          Your glucose patterns and insights
        </p>
      </header>

      {/* Placeholder Content */}
      <section className="px-4 py-6">
        <Card variant="outlined">
          <CardContent>
            <div className="text-center py-12">
              <div className="w-16 h-16 rounded-full bg-[#F6F7F9] mx-auto mb-4 flex items-center justify-center">
                <TrendsIcon size={32} color="#8A8E97" />
              </div>
              <h2 className="text-lg font-semibold text-[#1A1D21] mb-2">
                Trends Coming Soon
              </h2>
              <p className="text-sm text-[#8A8E97] max-w-xs mx-auto">
                As you log more glucose readings, we'll show you patterns,
                averages, and insights about your glucose management.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Mock Chart Placeholder */}
      <section className="px-4 py-6">
        <Card variant="outlined">
          <CardContent>
            <p className="font-semibold text-[#1A1D21] mb-4">
              7-Day Glucose Average
            </p>
            <div className="h-48 flex items-end justify-around gap-2">
              {[65, 72, 80, 75, 85, 70, 78].map((value, i) => (
                <div key={i} className="flex flex-col items-center gap-2">
                  <div
                    className="w-8 bg-[#315BFF] rounded-t"
                    style={{ height: `${value}%` }}
                  />
                  <span className="text-xs text-[#8A8E97]">
                    {['M', 'T', 'W', 'T', 'F', 'S', 'S'][i]}
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-[#E5E7EB] flex justify-between text-sm">
              <div>
                <p className="text-[#8A7E97]">Average</p>
                <p className="font-semibold text-[#1A1D21]">75 mg/dL</p>
              </div>
              <div>
                <p className="text-[#8A8E97]">Readings</p>
                <p className="font-semibold text-[#1A1D21]">42</p>
              </div>
              <div>
                <p className="text-[#8A8E97]">Time in Range</p>
                <p className="font-semibold text-[#10B981]">85%</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Coming Soon Features */}
      <section className="px-4 py-6">
        <Card variant="outlined">
          <CardContent>
            <h3 className="font-semibold text-[#1A1D21] mb-3">
              📈 Upcoming Features
            </h3>
            <ul className="space-y-2 text-sm text-[#8A8E97]">
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#315BFF]" />
                Daily/weekly glucose averages
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#315BFF]" />
                Meal impact analysis
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#315BFF]" />
                Cornstarch timing patterns
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#315BFF]" />
                Alert predictions
              </li>
            </ul>
          </CardContent>
        </Card>
      </section>
    </div>
  );
};
