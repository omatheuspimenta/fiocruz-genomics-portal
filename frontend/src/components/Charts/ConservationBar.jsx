import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const ConservationBar = ({ data }) => {
    return (
        <ResponsiveContainer width="100%" height="90%">
            <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={80} />
                <Tooltip />
                <Bar dataKey="avg" fill="#6366f1" radius={[0, 4, 4, 0]} name="Mean Score" barSize={20} />
                <Bar dataKey="max" fill="#cbd5e1" radius={[0, 4, 4, 0]} name="Max Score" barSize={20} />
            </BarChart>
        </ResponsiveContainer>
    );
};

export default ConservationBar;
