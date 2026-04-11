import React from 'react';
import { Card, CardContent } from '../components/Card';
import { WatchIcon } from '../components/Icons';

export const WatchPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#F6F7F9] pb-20">
      {/* Header */}
      <header className="bg-white px-4 py-6 border-b border-[#E5E7EB]">
        <h1 className="text-2xl font-bold text-[#1A1D21]">Watch</h1>
        <p className="text-sm text-[#8A8E97] mt-0.5">
          Research and educational content
        </p>
      </header>

      {/* Research Section */}
      <section className="px-4 py-6">
        <h2 className="text-sm font-semibold text-[#8A8E97] uppercase tracking-wide mb-3">
          Research
        </h2>
        <Card variant="outlined">
          <CardContent>
            <div className="text-center py-12">
              <div className="w-16 h-16 rounded-full bg-[#F6F7F9] mx-auto mb-4 flex items-center justify-center">
                <WatchIcon size={32} color="#8A8E97" />
              </div>
              <h2 className="text-lg font-semibold text-[#1A1D21] mb-2">
                Research Library
              </h2>
              <p className="text-sm text-[#8A8E97] max-w-xs mx-auto">
                Access peer-reviewed research about glycogen storage disease,
                cornstarch therapy, and glucose management.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Topics */}
      <section className="px-4 py-6">
        <h2 className="text-sm font-semibold text-[#8A8E97] uppercase tracking-wide mb-3">
          Topics
        </h2>
        <div className="space-y-3">
          {[
            {
              title: 'Understanding GSD',
              description: 'How glycogen storage disease affects glucose metabolism',
              icon: '🧬',
            },
            {
              title: 'Cornstarch Therapy',
              description: 'The science behind uncooked cornstarch for sustained glucose',
              icon: '🌽',
            },
            {
              title: 'Diet & Nutrition',
              description: 'Meal planning and carbohydrate management',
              icon: '🥗',
            },
            {
              title: 'Exercise & Activity',
              description: 'Managing glucose during physical activity',
              icon: '🏃',
            },
            {
              title: 'Monitoring Best Practices',
              description: 'When and how to check glucose levels',
              icon: '📊',
            },
          ].map((topic) => (
            <Card key={topic.title} variant="outlined">
              <CardContent>
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{topic.icon}</span>
                  <div>
                    <p className="font-semibold text-[#1A1D21]">{topic.title}</p>
                    <p className="text-sm text-[#8A8E97] mt-0.5">
                      {topic.description}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Coming Soon */}
      <section className="px-4 py-6">
        <Card variant="outlined">
          <CardContent>
            <div className="bg-[#FEF3C7] rounded-xl p-4">
              <p className="font-semibold text-[#92400E] mb-1">🚧 Coming Soon</p>
              <p className="text-sm text-[#92400E]">
                Research articles and educational materials will be available
                here. Stay tuned!
              </p>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
};
