import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const QualityHistogram = ({ data }) => {
    return (
        <ResponsiveContainer width="100%" height="90%">
            <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip cursor={{ fill: '#f8fafc' }} />
                <Bar dataKey="value" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Count" />
            </BarChart>
        </ResponsiveContainer>
    );
};

export default QualityHistogram;
