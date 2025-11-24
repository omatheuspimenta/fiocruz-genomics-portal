import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const PopulationBar = ({ data }) => {
    return (
        <ResponsiveContainer width="100%" height="90%">
            <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} dy={10} />
                <YAxis tickFormatter={(val) => val.toExponential(1)} tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }} />
                <Bar dataKey="val" fill="#0ea5e9" radius={[6, 6, 0, 0]} barSize={60} name="Mean AF" />
            </BarChart>
        </ResponsiveContainer>
    );
};

export default PopulationBar;
